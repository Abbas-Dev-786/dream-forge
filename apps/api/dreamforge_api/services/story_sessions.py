from __future__ import annotations

import json
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from dreamforge_api.clients.story_crew import StoryCrewClient
from dreamforge_api.config import Settings
from dreamforge_api.models import MediaJobRecord, StoryChoiceRecord, StoryNodeRecord, StorySessionRecord
from dreamforge_api.schemas import (
    AssetState,
    AssetStatus,
    ContinuationCrewInput,
    OpeningCrewInput,
    PromptConstraints,
    StoryBible,
    StoryChoicePayload,
    StoryChoiceRequest,
    StoryNodeResponse,
    StorySessionCreateRequest,
    StorySessionCreateResponse,
    StorySessionSummaryResponse,
)
from dreamforge_api.security import assert_safe_prompt


IMAGE_NEGATIVE_PROMPT = "blurry, distorted, dark horror imagery, gore, text overlay, watermark"


class StorySessionService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.crew = StoryCrewClient(settings)

    def create_story_session(self, request: StorySessionCreateRequest) -> StorySessionCreateResponse:
        assert_safe_prompt([request.child_name, request.theme, *request.interests])
        constraints = PromptConstraints(language=request.language)
        opening = self.crew.create_opening(
            OpeningCrewInput(
                mode="create_opening_scene",
                child_profile={
                    "name": request.child_name,
                    "age": request.child_age,
                    "interests": request.interests,
                },
                story_request={"theme": request.theme, "tone": request.tone.value},
                constraints=constraints,
            )
        )

        session = StorySessionRecord(
            id=self._generate_id("st"),
            share_slug=secrets.token_urlsafe(9).replace("-", "").replace("_", "")[:12],
            child_name=request.child_name,
            child_age=request.child_age,
            interests_json=json.dumps(request.interests),
            theme=request.theme,
            tone=request.tone.value,
            language=request.language,
            story_bible_json=opening.story_bible.model_dump_json(),
            status="READY_PARTIAL",
            expires_at=datetime.now(UTC) + timedelta(hours=self.settings.session_retention_hours),
        )
        node = StoryNodeRecord(
            id=self._generate_id("node"),
            session_id=session.id,
            parent_node_id=None,
            branch_depth=opening.scene_brief.branch_depth,
            title=opening.scene_brief.title,
            scene_summary=opening.scene_brief.scene_summary,
            story_text=opening.story_text,
            narration_text=opening.narration_text,
            illustration_prompt=opening.illustration_prompt,
            is_terminal=opening.is_terminal,
            image_status=AssetStatus.PENDING.value,
            audio_status=AssetStatus.PENDING.value,
        )
        session.current_node_id = node.id
        self.db.add(session)
        self.db.add(node)
        self.db.flush()
        self._persist_choices(node.id, opening.choices)
        self._enqueue_media_jobs(session.id, node.id, opening.illustration_prompt, opening.narration_text)
        self.db.commit()
        return self.build_create_response(session.id, node.id)

    def select_choice(self, story_id: str, request: StoryChoiceRequest) -> StorySessionCreateResponse:
        session = self._get_session(story_id)
        node = self._get_node(story_id, request.node_id)
        choice = self.db.scalar(
            select(StoryChoiceRecord).where(
                StoryChoiceRecord.node_id == node.id,
                StoryChoiceRecord.choice_key == request.choice_id,
            )
        )
        if not choice:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Choice not found.")
        if choice.next_node_id:
            session.current_node_id = choice.next_node_id
            self.db.commit()
            return self.build_create_response(session.id, choice.next_node_id)
        if node.is_terminal:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This node is already terminal.")

        current_depth = node.branch_depth + 1
        crew_output = self.crew.continue_story(
            ContinuationCrewInput(
                mode="continue_story_from_choice",
                story_bible=self._story_bible(session),
                current_node={
                    "node_id": node.id,
                    "title": node.title,
                    "scene_summary": node.scene_summary,
                },
                selected_choice=StoryChoicePayload(choice_id=choice.choice_key, label=choice.label),
                constraints={
                    "current_depth": current_depth,
                    "max_branch_depth": 2,
                    "remaining_node_budget": max(0, 7 - self._generated_count(session.id)),
                    "language": session.language,
                },
            )
        )

        next_node = StoryNodeRecord(
            id=self._generate_id("node"),
            session_id=session.id,
            parent_node_id=node.id,
            branch_depth=crew_output.scene_brief.branch_depth,
            title=crew_output.scene_brief.title,
            scene_summary=crew_output.scene_brief.scene_summary,
            story_text=crew_output.story_text,
            narration_text=crew_output.narration_text,
            illustration_prompt=crew_output.illustration_prompt,
            is_terminal=crew_output.is_terminal,
            image_status=AssetStatus.PENDING.value,
            audio_status=AssetStatus.PENDING.value,
        )
        self.db.add(next_node)
        self.db.flush()
        self._persist_choices(next_node.id, crew_output.choices)
        self._enqueue_media_jobs(session.id, next_node.id, crew_output.illustration_prompt, crew_output.narration_text)
        choice.next_node_id = next_node.id
        session.current_node_id = next_node.id
        session.status = "READY_PARTIAL"
        self.db.commit()
        return self.build_create_response(session.id, next_node.id)

    def get_story_session(self, story_id: str) -> StorySessionSummaryResponse:
        session = self._get_session(story_id)
        return StorySessionSummaryResponse(
            story_id=session.id,
            share_slug=session.share_slug,
            status=session.status,
            current_node_id=session.current_node_id or "",
            expires_at=session.expires_at,
        )

    def get_story_session_by_share_slug(self, share_slug: str) -> StorySessionSummaryResponse:
        session = self.db.scalar(select(StorySessionRecord).where(StorySessionRecord.share_slug == share_slug))
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Story session not found.")
        return self.get_story_session(session.id)

    def get_story_node(self, story_id: str, node_id: str) -> StoryNodeResponse:
        node = self._get_node(story_id, node_id)
        return self._build_node_response(node)

    def build_create_response(self, story_id: str, node_id: str) -> StorySessionCreateResponse:
        summary = self.get_story_session(story_id)
        return StorySessionCreateResponse(
            **summary.model_dump(),
            node=self.get_story_node(story_id, node_id),
        )

    def _persist_choices(self, node_id: str, choices: list[StoryChoicePayload]) -> None:
        for choice in choices:
            self.db.add(
                StoryChoiceRecord(
                    node_id=node_id,
                    choice_key=choice.choice_id,
                    label=choice.label,
                )
            )

    def _enqueue_media_jobs(self, session_id: str, node_id: str, illustration_prompt: str, narration_text: str) -> None:
        image_payload = {
            "prompt": illustration_prompt,
            "output_format": "landscape_4_3",
            "num_inference_steps": 4,
            "guidance_scale": 3.5,
            "num_images": 1,
            "enable_safety_checker": True,
            "negative_prompt": IMAGE_NEGATIVE_PROMPT,
        }
        audio_payload = {"text": narration_text}
        self.db.add(
            MediaJobRecord(
                id=self._generate_id("job"),
                session_id=session_id,
                node_id=node_id,
                job_type="IMAGE_RENDER",
                payload_json=json.dumps(image_payload),
            )
        )
        self.db.add(
            MediaJobRecord(
                id=self._generate_id("job"),
                session_id=session_id,
                node_id=node_id,
                job_type="AUDIO_RENDER",
                payload_json=json.dumps(audio_payload),
            )
        )

    def _build_node_response(self, node: StoryNodeRecord) -> StoryNodeResponse:
        choices = self.db.scalars(select(StoryChoiceRecord).where(StoryChoiceRecord.node_id == node.id)).all()
        return StoryNodeResponse(
            node_id=node.id,
            title=node.title,
            scene_summary=node.scene_summary,
            story_text=node.story_text,
            narration_text=node.narration_text,
            image=AssetState(status=AssetStatus(node.image_status), url=node.image_url),
            audio=AssetState(status=AssetStatus(node.audio_status), url=node.audio_url),
            choices=[StoryChoicePayload(choice_id=item.choice_key, label=item.label) for item in choices],
            is_terminal=node.is_terminal,
        )

    def _story_bible(self, session: StorySessionRecord) -> StoryBible:
        return StoryBible.model_validate_json(session.story_bible_json)

    def _generated_count(self, session_id: str) -> int:
        return len(
            self.db.scalars(select(StoryNodeRecord).where(StoryNodeRecord.session_id == session_id)).all()
        )

    def _get_session(self, story_id: str) -> StorySessionRecord:
        session = self.db.get(StorySessionRecord, story_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Story session not found.")
        expires_at = session.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at <= datetime.now(UTC):
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="Story session expired.")
        return session

    def _get_node(self, story_id: str, node_id: str) -> StoryNodeRecord:
        self._get_session(story_id)
        node = self.db.get(StoryNodeRecord, node_id)
        if not node or node.session_id != story_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Story node not found.")
        return node

    def _generate_id(self, prefix: str) -> str:
        return f"{prefix}_{secrets.token_urlsafe(8).replace('-', '').replace('_', '')[:12]}"
