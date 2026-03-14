from __future__ import annotations

from dreamforge_api.schemas import (
    ContinuationCrewInput,
    ContinuationCrewOutput,
    OpeningCrewInput,
    OpeningCrewOutput,
    SceneBrief,
    StoryBible,
    StoryChoicePayload,
)


def age_band_for(age: int) -> str:
    if age <= 7:
        return "5-7"
    if age <= 10:
        return "8-10"
    return "11-14"


class MockStoryCrew:
    def create_opening(self, payload: OpeningCrewInput) -> OpeningCrewOutput:
        name = str(payload.child_profile["name"])
        age = int(payload.child_profile["age"])
        interests = [str(item) for item in payload.child_profile["interests"]]
        theme = str(payload.story_request["theme"])
        appearance = f"{name}, a bright explorer with a star-map satchel and comet-blue scarf"
        story_bible = StoryBible(
            hero_profile={
                "name": name,
                "age": age,
                "appearance": appearance,
                "traits": ["curious", "kind", "brave"],
            },
            world_rules={
                "setting": f"a child-friendly {theme} world filled with floating lanterns and gentle surprises",
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
        brief = SceneBrief(
            title="The First Star Door",
            scene_summary=f"{name} discovers a glowing door that opens toward {theme} and notices clues linked to {', '.join(interests)}.",
            branch_depth=0,
        )
        prompt = self._illustration_prompt(story_bible, brief)
        return OpeningCrewOutput(
            story_bible=story_bible,
            scene_brief=brief,
            story_text=self._story_text(name, brief.scene_summary),
            narration_text=self._story_text(name, brief.scene_summary),
            illustration_prompt=prompt,
            choices=self._choices(name, 0),
            is_terminal=False,
        )

    def continue_story(self, payload: ContinuationCrewInput) -> ContinuationCrewOutput:
        name = payload.story_bible.hero_profile.name
        current_depth = int(payload.constraints.get("current_depth", 1))
        theme_hint = payload.selected_choice.label.lower()
        summary = f"{name} follows the path created by the choice '{payload.selected_choice.label}' and finds a new wonder that rewards bravery and kindness."
        brief = SceneBrief(
            title=self._continuation_title(theme_hint, current_depth),
            scene_summary=summary,
            branch_depth=current_depth,
        )
        is_terminal = current_depth >= int(payload.constraints.get("max_branch_depth", 2))
        return ContinuationCrewOutput(
            scene_brief=brief,
            story_text=self._story_text(name, summary),
            narration_text=self._story_text(name, summary),
            illustration_prompt=self._illustration_prompt(payload.story_bible, brief),
            choices=[] if is_terminal else self._choices(name, current_depth),
            is_terminal=is_terminal,
        )

    def _story_text(self, name: str, scene_summary: str) -> str:
        return (
            f"{name} took a steady breath and stepped forward with wide, wondering eyes. "
            f"{scene_summary} Tiny lights drifted around like patient fireflies, and every glow seemed to answer the kindness in {name}'s heart. "
            f"Whenever the path felt uncertain, the star-map satchel gave a soft shimmer, reminding {name} to stay brave, stay gentle, and keep moving toward the next surprise."
        )

    def _choices(self, name: str, depth: int) -> list[StoryChoicePayload]:
        return [
            StoryChoicePayload(choice_id="A", label=f"Follow the singing lantern trail with {name}"),
            StoryChoicePayload(choice_id="B", label=f"Open the moonlit gate at depth {depth + 1}"),
        ]

    def _illustration_prompt(self, story_bible: StoryBible, brief: SceneBrief) -> str:
        return (
            "Children's storybook illustration. "
            f"Hero: {story_bible.hero_profile.appearance}. "
            f"World: {story_bible.world_rules.setting}. "
            f"Style: {story_bible.visual_style.look}, {story_bible.visual_style.palette}, {story_bible.visual_style.lighting}. "
            f"Scene: {brief.scene_summary}."
        )

    def _continuation_title(self, choice_label: str, depth: int) -> str:
        if "lantern" in choice_label:
            return f"The Lantern River {depth}"
        if "gate" in choice_label:
            return f"The Moonlit Gate {depth}"
        return f"The Next Wonder {depth}"

