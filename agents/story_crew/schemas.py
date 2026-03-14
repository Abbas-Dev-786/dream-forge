from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class StoryChoicePayload(BaseModel):
    choice_id: str
    label: str


class HeroProfile(BaseModel):
    name: str
    age: int
    appearance: str
    traits: list[str]


class WorldRules(BaseModel):
    setting: str
    magic_system: str
    safety_constraints: list[str]


class VisualStyle(BaseModel):
    look: str
    palette: str
    lighting: str


class StoryBible(BaseModel):
    hero_profile: HeroProfile
    world_rules: WorldRules
    visual_style: VisualStyle
    continuity_facts: list[str]


class SceneBrief(BaseModel):
    title: str
    scene_summary: str
    branch_depth: int


class OpeningOutput(BaseModel):
    story_bible: StoryBible
    scene_brief: SceneBrief
    story_text: str
    narration_text: str
    illustration_prompt: str
    choices: list[StoryChoicePayload]
    is_terminal: bool = False

    @model_validator(mode="after")
    def validate_choices(self) -> "OpeningOutput":
        if not self.is_terminal and len(self.choices) != 2:
            raise ValueError("Opening outputs must include exactly 2 choices.")
        return self


class ContinuationOutput(BaseModel):
    scene_brief: SceneBrief
    story_text: str
    narration_text: str
    illustration_prompt: str
    choices: list[StoryChoicePayload]
    is_terminal: bool = False

    @model_validator(mode="after")
    def validate_choices(self) -> "ContinuationOutput":
        if not self.is_terminal and len(self.choices) != 2:
            raise ValueError("Continuation outputs must include exactly 2 choices.")
        return self


class OpeningInput(BaseModel):
    mode: Literal["create_opening_scene"]
    child_profile: dict[str, object]
    story_request: dict[str, object]
    constraints: dict[str, object]


class ContinuationInput(BaseModel):
    mode: Literal["continue_story_from_choice"]
    story_bible: StoryBible
    current_node: dict[str, object]
    selected_choice: StoryChoicePayload
    constraints: dict[str, object]
