from __future__ import annotations

import json

import httpx
from pydantic import ValidationError

from dreamforge_api.config import Settings
from dreamforge_api.mock_crew import MockStoryCrew
from dreamforge_api.schemas import ContinuationCrewInput, ContinuationCrewOutput, OpeningCrewInput, OpeningCrewOutput


class StoryCrewError(RuntimeError):
    pass


class StoryCrewClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.mock_crew = MockStoryCrew()

    def create_opening(self, payload: OpeningCrewInput) -> OpeningCrewOutput:
        if self.settings.use_mock_ai or not self.settings.story_crew_run_url:
            return self.mock_crew.create_opening(payload)
        raw = self._invoke(payload.model_dump(mode="json"))
        try:
            return OpeningCrewOutput.model_validate(raw)
        except ValidationError as exc:
            raise StoryCrewError(f"Invalid opening output from story crew: {exc}") from exc

    def continue_story(self, payload: ContinuationCrewInput) -> ContinuationCrewOutput:
        if self.settings.use_mock_ai or not self.settings.story_crew_run_url:
            return self.mock_crew.continue_story(payload)
        raw = self._invoke(payload.model_dump(mode="json"))
        try:
            return ContinuationCrewOutput.model_validate(raw)
        except ValidationError as exc:
            raise StoryCrewError(f"Invalid continuation output from story crew: {exc}") from exc

    def _invoke(self, payload: dict[str, object]) -> dict[str, object]:
        headers = {"Content-Type": "application/json"}
        if self.settings.digitalocean_api_token and "localhost" not in self.settings.story_crew_run_url:
            headers["Authorization"] = f"Bearer {self.settings.digitalocean_api_token}"
        response = httpx.post(
            self.settings.story_crew_run_url,
            headers=headers,
            json={"prompt": payload},
            timeout=60.0,
        )
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict) and "response" in data:
            raw = data["response"]
        else:
            raw = data
        if isinstance(raw, str):
            try:
                return json.loads(raw)
            except json.JSONDecodeError as exc:
                raise StoryCrewError("Story crew returned a non-JSON string response.") from exc
        if isinstance(raw, dict):
            return raw
        raise StoryCrewError("Story crew returned an unsupported payload shape.")

