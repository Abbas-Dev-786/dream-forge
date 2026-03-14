from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, StringConstraints, model_validator
from typing_extensions import Annotated


SafeName = Annotated[str, StringConstraints(min_length=1, max_length=24, strip_whitespace=True)]
ShortText = Annotated[str, StringConstraints(min_length=1, max_length=160, strip_whitespace=True)]


class Tone(str, Enum):
    GENTLE = "gentle"
    FUNNY = "funny"
    ADVENTUROUS = "adventurous"
    EDUCATIONAL = "educational"


class AssetStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


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


class StoryMemory(BaseModel):
    branch_summaries: list[str] = Field(default_factory=list)


class SceneBrief(BaseModel):
    title: str
    scene_summary: str
    branch_depth: int


class StorySessionCreateRequest(BaseModel):
    child_name: SafeName
    child_age: int = Field(ge=5, le=14)
    interests: list[ShortText] = Field(min_length=1, max_length=3)
    theme: ShortText
    tone: Tone
    language: Literal["en"] = "en"


class StoryChoiceRequest(BaseModel):
    node_id: str
    choice_id: str


class AssetState(BaseModel):
    status: AssetStatus
    url: str | None = None


class StoryNodeResponse(BaseModel):
    node_id: str
    title: str
    scene_summary: str
    story_text: str
    narration_text: str
    image: AssetState
    audio: AssetState
    choices: list[StoryChoicePayload]
    is_terminal: bool


class StorySessionSummaryResponse(BaseModel):
    story_id: str
    share_slug: str
    status: str
    current_node_id: str
    expires_at: datetime


class StorySessionCreateResponse(StorySessionSummaryResponse):
    node: StoryNodeResponse


class PromptConstraints(BaseModel):
    max_branch_depth: int = 2
    max_total_nodes: int = 7
    language: Literal["en"] = "en"


class OpeningCrewInput(BaseModel):
    mode: Literal["create_opening_scene"]
    child_profile: dict[str, object]
    story_request: dict[str, object]
    constraints: PromptConstraints


class ContinuationCrewInput(BaseModel):
    mode: Literal["continue_story_from_choice"]
    story_bible: StoryBible
    story_memory: StoryMemory = Field(default_factory=StoryMemory)
    current_node: dict[str, object]
    selected_choice: StoryChoicePayload
    tone: Tone
    constraints: dict[str, object]


class OpeningCrewOutput(BaseModel):
    story_bible: StoryBible
    story_memory: StoryMemory = Field(default_factory=StoryMemory)
    scene_brief: SceneBrief
    story_text: str
    narration_text: str
    illustration_prompt: str
    choices: list[StoryChoicePayload]
    is_terminal: bool = False

    @model_validator(mode="after")
    def validate_choice_count(self) -> "OpeningCrewOutput":
        if not self.is_terminal and len(self.choices) != 2:
            raise ValueError("Opening scene must return exactly 2 choices unless terminal.")
        return self


class ContinuationCrewOutput(BaseModel):
    story_memory: StoryMemory = Field(default_factory=StoryMemory)
    scene_brief: SceneBrief
    story_text: str
    narration_text: str
    illustration_prompt: str
    choices: list[StoryChoicePayload]
    is_terminal: bool = False

    @model_validator(mode="after")
    def validate_choice_count(self) -> "ContinuationCrewOutput":
        if not self.is_terminal and len(self.choices) != 2:
            raise ValueError("Continuation scene must return exactly 2 choices unless terminal.")
        return self
