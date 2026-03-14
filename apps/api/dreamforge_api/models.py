from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from dreamforge_api.db import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class StorySessionRecord(Base):
    __tablename__ = "story_sessions"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    share_slug: Mapped[str] = mapped_column(Text, unique=True, index=True)
    child_name: Mapped[str] = mapped_column(Text)
    child_age: Mapped[int] = mapped_column(Integer)
    interests_json: Mapped[str] = mapped_column(Text)
    theme: Mapped[str] = mapped_column(Text)
    tone: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(Text, default="en")
    story_bible_json: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, default="READY_PARTIAL")
    current_node_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class StoryNodeRecord(Base):
    __tablename__ = "story_nodes"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("story_sessions.id"), index=True)
    parent_node_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    branch_depth: Mapped[int] = mapped_column(Integer, default=0)
    title: Mapped[str] = mapped_column(Text)
    scene_summary: Mapped[str] = mapped_column(Text)
    story_text: Mapped[str] = mapped_column(Text)
    narration_text: Mapped[str] = mapped_column(Text)
    illustration_prompt: Mapped[str] = mapped_column(Text)
    story_memory_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_terminal: Mapped[bool] = mapped_column(Boolean, default=False)
    image_status: Mapped[str] = mapped_column(Text, default="pending")
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    audio_status: Mapped[str] = mapped_column(Text, default="pending")
    audio_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class StoryChoiceRecord(Base):
    __tablename__ = "story_choices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    node_id: Mapped[str] = mapped_column(ForeignKey("story_nodes.id"), index=True)
    choice_key: Mapped[str] = mapped_column(Text)
    label: Mapped[str] = mapped_column(Text)
    next_node_id: Mapped[str | None] = mapped_column(Text, nullable=True)


class MediaJobRecord(Base):
    __tablename__ = "media_jobs"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("story_sessions.id"), index=True)
    node_id: Mapped[str] = mapped_column(ForeignKey("story_nodes.id"), index=True)
    job_type: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, default="queued", index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    payload_json: Mapped[str] = mapped_column(Text)
    external_request_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class MediaAssetRecord(Base):
    __tablename__ = "media_assets"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("story_sessions.id"), index=True)
    node_id: Mapped[str] = mapped_column(ForeignKey("story_nodes.id"), index=True)
    asset_type: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)
    provider_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
