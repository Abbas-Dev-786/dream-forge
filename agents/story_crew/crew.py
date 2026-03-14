from __future__ import annotations

import json
import os
from typing import TypedDict

import httpx
from langgraph.graph import END, StateGraph

from prompts import (
    interaction_example_output,
    interaction_prompt,
    json_message,
    memory_example_output,
    memory_prompt,
    narrative_example_input,
    narrative_example_output,
    narrative_prompt,
    planner_continuation_example_output,
    planner_continuation_prompt,
    planner_opening_example_input,
    planner_opening_example_output,
    planner_opening_prompt,
    reviewer_example_output,
    reviewer_prompt,
)
from schemas import (
    ContinuationInput,
    ContinuationOutput,
    MemoryUpdate,
    OpeningInput,
    OpeningOutput,
    ReviewDecision,
    SceneBrief,
    StoryBible,
    StoryChoicePayload,
    StoryMemory,
)


class CrewState(TypedDict, total=False):
    request: dict[str, object]
    story_bible: dict[str, object]
    story_memory: dict[str, object]
    scene_brief: dict[str, object]
    story_text: str
    narration_text: str
    illustration_prompt: str
    choices: list[dict[str, str]]
    is_terminal: bool
    critique: str
    review_attempts: int
    reviewer_approved: bool
    review_severity: str
    draft_output: dict[str, object]
    output: dict[str, object]


class StoryCrewRuntime:
    def __init__(self) -> None:
        self.use_mock_ai = os.getenv("DREAMFORGE_USE_MOCK_AI", "true").lower() == "true"
        self.model_access_key = os.getenv("GRADIENT_MODEL_ACCESS_KEY")
        self.model_id = os.getenv("STORY_CREW_MODEL_ID", "anthropic-claude-4.6-sonnet")
        self.reviewer_model_id = os.getenv("REVIEWER_MODEL_ID", "openai-gpt-4.1-mini")
        self.memory_model_id = os.getenv("MEMORY_MODEL_ID", self.reviewer_model_id)
        self.inference_base_url = os.getenv("INFERENCE_BASE_URL", "https://inference.do-ai.run")
        self.graph = self._build_graph()

    def run(self, payload: dict[str, object]) -> dict[str, object]:
        result = self.graph.invoke({"request": payload, "review_attempts": 0, "critique": ""})
        return result["output"]

    def _build_graph(self):
        graph = StateGraph(CrewState)
        graph.add_node("planner", self._planner)
        graph.add_node("narrative", self._narrative)
        graph.add_node("interaction", self._interaction)
        graph.add_node("reviewer", self._reviewer)
        graph.add_node("review_pass", self._review_pass)
        graph.add_node("fallback", self._fallback)
        graph.add_node("compose", self._compose)
        graph.add_node("memory_updater", self._memory_updater)
        graph.set_entry_point("planner")
        graph.add_edge("planner", "narrative")
        graph.add_edge("planner", "interaction")
        graph.add_edge("narrative", "reviewer")
        graph.add_conditional_edges(
            "reviewer",
            self._review_route,
            {
                "rewrite": "narrative",
                "approved": "review_pass",
                "fallback": "fallback",
            },
        )
        graph.add_edge(["interaction", "review_pass"], "compose")
        graph.add_edge(["interaction", "fallback"], "compose")
        graph.add_edge("compose", "memory_updater")
        graph.add_edge("memory_updater", END)
        return graph.compile()

    def _planner(self, state: CrewState) -> CrewState:
        request = state["request"]
        mode = str(request["mode"])
        if mode == "create_opening_scene":
            parsed = OpeningInput.model_validate(request)
            if self._should_mock():
                story_bible = self._mock_story_bible(parsed)
                scene_brief = SceneBrief(
                    title="The First Star Door",
                    scene_summary=f"{parsed.child_profile['name']} discovers a glowing door that points toward {parsed.story_request['theme']} and the first brave choice.",
                    branch_depth=0,
                )
            else:
                raw = self._chat_json(
                    model=self.model_id,
                    system_prompt=planner_opening_prompt(),
                    user_payload=parsed.model_dump(mode="json"),
                    example_input=planner_opening_example_input(),
                    example_output=planner_opening_example_output(),
                    temperature=0.2,
                )
                story_bible = StoryBible.model_validate(raw["story_bible"])
                scene_brief = SceneBrief.model_validate(raw["scene_brief"])
            return {
                "story_bible": story_bible.model_dump(mode="json"),
                "story_memory": StoryMemory().model_dump(mode="json"),
                "scene_brief": scene_brief.model_dump(mode="json"),
                "review_attempts": 0,
                "critique": "",
            }

        parsed = ContinuationInput.model_validate(request)
        if self._should_mock():
            scene_brief = SceneBrief(
                title=self._mock_continuation_title(parsed.selected_choice.label, int(parsed.constraints.get("current_depth", 1))),
                scene_summary=(
                    f"{parsed.story_bible.hero_profile.name} follows the choice '{parsed.selected_choice.label}' "
                    "and uncovers a new clue that builds on the same magical world."
                ),
                branch_depth=int(parsed.constraints.get("current_depth", 1)),
            )
        else:
            raw = self._chat_json(
                model=self.model_id,
                system_prompt=planner_continuation_prompt(),
                user_payload=parsed.model_dump(mode="json"),
                example_output=planner_continuation_example_output(),
                temperature=0.2,
            )
            scene_brief = SceneBrief.model_validate(raw["scene_brief"])
        return {
            "story_bible": parsed.story_bible.model_dump(mode="json"),
            "story_memory": parsed.story_memory.model_dump(mode="json"),
            "scene_brief": scene_brief.model_dump(mode="json"),
            "review_attempts": 0,
            "critique": "",
        }

    def _narrative(self, state: CrewState) -> CrewState:
        story_bible = StoryBible.model_validate(state["story_bible"])
        story_memory = StoryMemory.model_validate(state.get("story_memory", {}))
        scene_brief = SceneBrief.model_validate(state["scene_brief"])
        tone = self._tone(state["request"])
        critique = state.get("critique", "")
        if self._should_mock():
            story_text = self._mock_story_text(story_bible.hero_profile.name, scene_brief.scene_summary, critique)
            illustration_prompt = self._mock_illustration_prompt(story_bible, scene_brief)
        else:
            raw = self._chat_json(
                model=self.model_id,
                system_prompt=narrative_prompt(story_bible, scene_brief, tone, story_memory, critique),
                user_payload={
                    "story_bible": story_bible.model_dump(mode="json"),
                    "scene_brief": scene_brief.model_dump(mode="json"),
                    "tone": tone,
                    "story_memory": story_memory.model_dump(mode="json"),
                    "critique": critique,
                },
                example_input=narrative_example_input(story_bible, scene_brief, tone),
                example_output=narrative_example_output(story_bible),
                temperature=0.35,
            )
            story_text = str(raw["story_text"])
            illustration_prompt = str(raw["illustration_prompt"])
            return {
                "story_text": story_text,
                "narration_text": str(raw["narration_text"]),
                "illustration_prompt": illustration_prompt,
            }
        return {
            "story_text": story_text,
            "narration_text": story_text,
            "illustration_prompt": illustration_prompt,
        }

    def _interaction(self, state: CrewState) -> CrewState:
        request = state["request"]
        story_bible = StoryBible.model_validate(state["story_bible"])
        story_memory = StoryMemory.model_validate(state.get("story_memory", {}))
        scene_brief = SceneBrief.model_validate(state["scene_brief"])
        tone = self._tone(request)
        if self._should_mock():
            max_depth = int(request.get("constraints", {}).get("max_branch_depth", 2))
            if str(request["mode"]) == "continue_story_from_choice" and scene_brief.branch_depth >= max_depth:
                return {"choices": [], "is_terminal": True}
            return {
                "choices": self._mock_choices(scene_brief.branch_depth),
                "is_terminal": False,
            }

        raw = self._chat_json(
            model=self.model_id,
            system_prompt=interaction_prompt(story_bible, scene_brief, tone, story_memory),
            user_payload={
                "scene_brief": scene_brief.model_dump(mode="json"),
                "story_memory": story_memory.model_dump(mode="json"),
                "tone": tone,
            },
            example_output=interaction_example_output(),
            temperature=0.25,
        )
        return {
            "choices": raw["choices"],
            "is_terminal": bool(raw["is_terminal"]),
        }

    def _reviewer(self, state: CrewState) -> CrewState:
        story_bible = StoryBible.model_validate(state["story_bible"])
        tone = self._tone(state["request"])
        attempts = int(state.get("review_attempts", 0))
        story_text = state["story_text"]
        narration_text = state["narration_text"]
        if self._should_mock():
            decision = self._mock_review(story_bible, tone, story_text, narration_text)
        else:
            raw = self._chat_json(
                model=self.reviewer_model_id,
                system_prompt=reviewer_prompt(story_bible, tone, story_text, narration_text),
                user_payload={
                    "story_text": story_text,
                    "narration_text": narration_text,
                },
                example_output=reviewer_example_output(True),
                temperature=0.1,
            )
            decision = ReviewDecision.model_validate(raw)
        return {
            "reviewer_approved": decision.approved,
            "critique": decision.critique,
            "review_severity": decision.severity,
            "review_attempts": attempts + (0 if decision.approved else 1),
        }

    def _review_pass(self, state: CrewState) -> CrewState:
        return state

    def _fallback(self, state: CrewState) -> CrewState:
        story_bible = StoryBible.model_validate(state["story_bible"])
        scene_brief = SceneBrief.model_validate(state["scene_brief"])
        safe_text = (
            f"{story_bible.hero_profile.name} paused, looked around carefully, and noticed that the whole place felt warm and welcoming again. "
            f"{scene_brief.scene_summary} "
            f"Nothing in the scene felt frightening now. Instead, the path glowed softly and invited {story_bible.hero_profile.name} to keep exploring with calm courage."
        )
        return {
            "story_text": safe_text,
            "narration_text": safe_text,
            "illustration_prompt": self._mock_illustration_prompt(story_bible, scene_brief),
            "critique": "Fallback applied after the second failed review pass.",
        }

    def _compose(self, state: CrewState) -> CrewState:
        request = state["request"]
        shared = {
            "scene_brief": state["scene_brief"],
            "story_text": state["story_text"],
            "narration_text": state["narration_text"],
            "illustration_prompt": state["illustration_prompt"],
            "choices": state["choices"],
            "is_terminal": state["is_terminal"],
        }
        if str(request["mode"]) == "create_opening_scene":
            output = OpeningOutput(
                story_bible=StoryBible.model_validate(state["story_bible"]),
                story_memory=StoryMemory.model_validate(state["story_memory"]),
                **shared,
            )
            return {"draft_output": output.model_dump(mode="json")}
        output = ContinuationOutput(
            story_memory=StoryMemory.model_validate(state["story_memory"]),
            **shared,
        )
        return {"draft_output": output.model_dump(mode="json")}

    def _memory_updater(self, state: CrewState) -> CrewState:
        request = state["request"]
        story_bible = StoryBible.model_validate(state["story_bible"])
        scene_brief = SceneBrief.model_validate(state["scene_brief"])
        story_memory = StoryMemory.model_validate(state.get("story_memory", {}))
        selected_choice = None
        if str(request["mode"]) == "continue_story_from_choice":
            selected_choice = str(request["selected_choice"]["label"])

        if self._should_mock():
            memory_entry = self._mock_memory_entry(scene_brief, selected_choice)
        else:
            raw = self._chat_json(
                model=self.memory_model_id,
                system_prompt=memory_prompt(story_bible, scene_brief, story_memory, selected_choice),
                user_payload={
                    "story_memory": story_memory.model_dump(mode="json"),
                    "scene_brief": scene_brief.model_dump(mode="json"),
                    "selected_choice": selected_choice,
                },
                example_output=memory_example_output(),
                temperature=0.1,
            )
            memory_entry = MemoryUpdate.model_validate(raw).memory_entry

        next_memory = StoryMemory(branch_summaries=[*story_memory.branch_summaries, memory_entry])
        draft_output = dict(state["draft_output"])
        draft_output["story_memory"] = next_memory.model_dump(mode="json")
        return {
            "story_memory": next_memory.model_dump(mode="json"),
            "output": draft_output,
        }

    def _review_route(self, state: CrewState) -> str:
        if state.get("reviewer_approved", False):
            return "approved"
        if int(state.get("review_attempts", 0)) < 2:
            return "rewrite"
        return "fallback"

    def _should_mock(self) -> bool:
        return self.use_mock_ai or not self.model_access_key

    def _tone(self, request: dict[str, object]) -> str:
        if str(request["mode"]) == "create_opening_scene":
            return str(request.get("story_request", {}).get("tone", "gentle"))
        return str(request.get("tone", "gentle"))

    def _chat_json(
        self,
        *,
        model: str,
        system_prompt: str,
        user_payload: dict[str, object],
        example_input: dict[str, object] | None = None,
        example_output: dict[str, object] | None = None,
        temperature: float,
    ) -> dict[str, object]:
        messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
        if example_input is not None and example_output is not None:
            messages.append({"role": "user", "content": json_message(example_input)})
            messages.append({"role": "assistant", "content": json_message(example_output)})
        elif example_output is not None:
            messages.append({"role": "assistant", "content": json_message(example_output)})
        messages.append({"role": "user", "content": json.dumps(user_payload)})
        response = httpx.post(
            f"{self.inference_base_url}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.model_access_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_completion_tokens": 1400,
            },
            timeout=60.0,
        )
        response.raise_for_status()
        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        if isinstance(content, list):
            content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
        return json.loads(content)

    def _mock_story_bible(self, payload: OpeningInput) -> StoryBible:
        name = str(payload.child_profile["name"])
        age = int(payload.child_profile["age"])
        theme = str(payload.story_request["theme"])
        interests = [str(item) for item in payload.child_profile["interests"]]
        return StoryBible(
            hero_profile={
                "name": name,
                "age": age,
                "appearance": f"{name}, a bright explorer with a star-map satchel and comet-blue scarf",
                "traits": ["curious", "kind", "brave"],
            },
            world_rules={
                "setting": f"a child-friendly {theme} world full of floating lights and welcoming doors",
                "magic_system": "kind choices make the starlight respond",
                "safety_constraints": ["no horror", "no violence", "no romance"],
            },
            visual_style={
                "look": "storybook adventure illustration",
                "palette": "sunrise oranges, cloud blues, and candy golds",
                "lighting": "warm cinematic glow",
            },
            continuity_facts=[
                f"{name} always carries a star-map satchel.",
                f"{name} loves {', '.join(interests)}.",
                f"{name} stays the hero of every scene.",
            ],
        )

    def _mock_story_text(self, name: str, summary: str, critique: str) -> str:
        softened_summary = summary
        if critique:
            for term in ("shadow", "spooky", "haunted", "creepy", "dark cave", "scary"):
                softened_summary = softened_summary.replace(term, "glowing lantern")
            softened_summary = softened_summary.replace("dark", "gentle")
        return (
            f"{name} stepped forward with a brave little smile. "
            f"{softened_summary} "
            f"Every glowing detail felt friendly instead of frightening, and the world seemed to brighten whenever {name} chose kindness over fear."
        )

    def _mock_illustration_prompt(self, story_bible: StoryBible, scene_brief: SceneBrief) -> str:
        return (
            f"{story_bible.hero_profile.appearance} in {scene_brief.scene_summary} within {story_bible.world_rules.setting}, "
            f"{story_bible.visual_style.lighting}, {story_bible.visual_style.look} with {story_bible.visual_style.palette}"
        )

    def _mock_choices(self, depth: int) -> list[dict[str, str]]:
        return [
            StoryChoicePayload(choice_id="A", label=f"Follow the singing lantern trail at turn {depth + 1}").model_dump(),
            StoryChoicePayload(choice_id="B", label=f"Open the moonlit gate at turn {depth + 1}").model_dump(),
        ]

    def _mock_review(self, story_bible: StoryBible, tone: str, story_text: str, narration_text: str) -> ReviewDecision:
        text = f"{story_text} {narration_text}".lower()
        flagged_terms = {"shadow", "spooky", "haunted", "monster", "creepy", "scary", "scarred", "dark cave"}
        if story_bible.hero_profile.age <= 7 and any(term in text for term in flagged_terms):
            return ReviewDecision(
                approved=False,
                critique="The imagery feels too scary for a young child. Rewrite it so the scene feels welcoming, bright, and gently magical.",
                severity="high",
            )
        if tone == "gentle" and "suddenly" in text:
            return ReviewDecision(
                approved=False,
                critique="The pacing feels too abrupt for a gentle tone. Slow it down and make the transition calmer.",
                severity="medium",
            )
        return ReviewDecision(approved=True, critique="The scene is warm, clear, and age-safe.", severity="low")

    def _mock_memory_entry(self, scene_brief: SceneBrief, selected_choice: str | None) -> str:
        if selected_choice:
            return f"After choosing '{selected_choice}', the hero reached '{scene_brief.title}' where {scene_brief.scene_summary}"
        return f"The story opened at '{scene_brief.title}' where {scene_brief.scene_summary}"

    def _mock_continuation_title(self, choice_label: str, depth: int) -> str:
        if "lantern" in choice_label.lower():
            return f"The Lantern River {depth}"
        if "gate" in choice_label.lower():
            return f"The Moonlit Gate {depth}"
        return f"The Next Wonder {depth}"
