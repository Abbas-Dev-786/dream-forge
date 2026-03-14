from __future__ import annotations

import json
import os
from typing import TypedDict

import httpx
from langgraph.graph import END, StateGraph

from schemas import ContinuationInput, ContinuationOutput, OpeningInput, OpeningOutput, SceneBrief, StoryBible, StoryChoicePayload


class CrewState(TypedDict, total=False):
    request: dict[str, object]
    story_bible: dict[str, object]
    scene_brief: dict[str, object]
    story_text: str
    narration_text: str
    illustration_prompt: str
    choices: list[dict[str, str]]
    is_terminal: bool
    output: dict[str, object]


class StoryCrewRuntime:
    def __init__(self) -> None:
        self.use_mock_ai = os.getenv("DREAMFORGE_USE_MOCK_AI", "true").lower() == "true"
        self.model_access_key = os.getenv("GRADIENT_MODEL_ACCESS_KEY")
        self.model_id = os.getenv("STORY_CREW_MODEL_ID", "anthropic-claude-4.6-sonnet")
        self.inference_base_url = os.getenv("INFERENCE_BASE_URL", "https://inference.do-ai.run")
        self.graph = self._build_graph()

    def run(self, payload: dict[str, object]) -> dict[str, object]:
        result = self.graph.invoke({"request": payload})
        return result["output"]

    def _build_graph(self):
        graph = StateGraph(CrewState)
        graph.add_node("planner", self._planner)
        graph.add_node("narrative", self._narrative)
        graph.add_node("interaction", self._interaction)
        graph.add_node("compose", self._compose)
        graph.set_entry_point("planner")
        graph.add_edge("planner", "narrative")
        graph.add_edge("narrative", "interaction")
        graph.add_edge("interaction", "compose")
        graph.add_edge("compose", END)
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
                    system_prompt=(
                        "You are the planner for a kid-safe story crew. "
                        "Return JSON only with keys story_bible and scene_brief."
                    ),
                    user_payload=parsed.model_dump(mode="json"),
                )
                story_bible = StoryBible.model_validate(raw["story_bible"])
                scene_brief = SceneBrief.model_validate(raw["scene_brief"])
            return {
                "story_bible": story_bible.model_dump(mode="json"),
                "scene_brief": scene_brief.model_dump(mode="json"),
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
                system_prompt=(
                    "You are the planner for a kid-safe story crew. "
                    "The story_bible is immutable. Return JSON only with key scene_brief."
                ),
                user_payload=parsed.model_dump(mode="json"),
            )
            scene_brief = SceneBrief.model_validate(raw["scene_brief"])
        return {
            "story_bible": parsed.story_bible.model_dump(mode="json"),
            "scene_brief": scene_brief.model_dump(mode="json"),
        }

    def _narrative(self, state: CrewState) -> CrewState:
        story_bible = StoryBible.model_validate(state["story_bible"])
        scene_brief = SceneBrief.model_validate(state["scene_brief"])
        if self._should_mock():
            story_text = self._mock_story_text(story_bible.hero_profile.name, scene_brief.scene_summary)
            illustration_prompt = self._mock_illustration_prompt(story_bible, scene_brief)
        else:
            raw = self._chat_json(
                system_prompt=(
                    "You are the narrative writer for a children's story crew. "
                    "Return JSON only with keys story_text, narration_text, illustration_prompt."
                ),
                user_payload={
                    "story_bible": story_bible.model_dump(mode="json"),
                    "scene_brief": scene_brief.model_dump(mode="json"),
                },
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
        scene_brief = SceneBrief.model_validate(state["scene_brief"])
        if self._should_mock():
            if str(request["mode"]) == "continue_story_from_choice" and scene_brief.branch_depth >= int(request["constraints"].get("max_branch_depth", 2)):
                return {"choices": [], "is_terminal": True}
            return {
                "choices": [
                    StoryChoicePayload(choice_id="A", label="Follow the singing lantern trail").model_dump(),
                    StoryChoicePayload(choice_id="B", label="Open the moonlit gate").model_dump(),
                ],
                "is_terminal": False,
            }

        raw = self._chat_json(
            system_prompt=(
                "You are the interaction designer for a children's story crew. "
                "Return JSON only with keys choices and is_terminal. "
                "For non-terminal scenes return exactly 2 choices."
            ),
            user_payload={
                "request": request,
                "scene_brief": scene_brief.model_dump(mode="json"),
            },
        )
        return {
            "choices": raw["choices"],
            "is_terminal": bool(raw["is_terminal"]),
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
                **shared,
            )
            return {"output": output.model_dump(mode="json")}
        output = ContinuationOutput(**shared)
        return {"output": output.model_dump(mode="json")}

    def _should_mock(self) -> bool:
        return self.use_mock_ai or not self.model_access_key

    def _chat_json(self, system_prompt: str, user_payload: dict[str, object]) -> dict[str, object]:
        response = httpx.post(
            f"{self.inference_base_url}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.model_access_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model_id,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(user_payload)},
                ],
                "temperature": 0.3,
                "max_completion_tokens": 1200,
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

    def _mock_story_text(self, name: str, summary: str) -> str:
        return (
            f"{name} stepped forward with a brave little smile. "
            f"{summary} "
            f"Every glowing detail felt friendly instead of frightening, and the world seemed to brighten whenever {name} chose kindness over fear."
        )

    def _mock_illustration_prompt(self, story_bible: StoryBible, scene_brief: SceneBrief) -> str:
        return (
            "Children's storybook illustration. "
            f"Hero: {story_bible.hero_profile.appearance}. "
            f"World: {story_bible.world_rules.setting}. "
            f"Style: {story_bible.visual_style.look}, {story_bible.visual_style.palette}, {story_bible.visual_style.lighting}. "
            f"Scene: {scene_brief.scene_summary}."
        )

    def _mock_continuation_title(self, choice_label: str, depth: int) -> str:
        if "lantern" in choice_label.lower():
            return f"The Lantern River {depth}"
        if "gate" in choice_label.lower():
            return f"The Moonlit Gate {depth}"
        return f"The Next Wonder {depth}"
