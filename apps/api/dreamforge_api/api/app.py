from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from sqlalchemy.orm import Session

from dreamforge_api.config import get_settings
from dreamforge_api.db import get_db, init_db
from dreamforge_api.models import MediaAssetRecord, StoryNodeRecord
from dreamforge_api.schemas import StoryChoiceRequest, StorySessionCreateRequest
from dreamforge_api.services.media_jobs import generate_mock_svg, generate_mock_wav_bytes
from dreamforge_api.services.story_sessions import StorySessionService


settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.auto_migrate:
        init_db()
    yield


app = FastAPI(title="DreamForge API", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_story_service(db: Session = Depends(get_db)) -> StorySessionService:
    return StorySessionService(db, settings)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/story-sessions")
def create_story_session(
    payload: StorySessionCreateRequest,
    service: StorySessionService = Depends(get_story_service),
):
    return service.create_story_session(payload)


@app.get("/api/v1/story-sessions/{story_id}")
def get_story_session(story_id: str, service: StorySessionService = Depends(get_story_service)):
    return service.get_story_session(story_id)


@app.get("/api/v1/story-sessions/by-share-slug/{share_slug}")
def get_story_session_by_share_slug(share_slug: str, service: StorySessionService = Depends(get_story_service)):
    return service.get_story_session_by_share_slug(share_slug)


@app.get("/api/v1/story-sessions/{story_id}/nodes/{node_id}")
def get_story_node(
    story_id: str,
    node_id: str,
    service: StorySessionService = Depends(get_story_service),
):
    return service.get_story_node(story_id, node_id)


@app.post("/api/v1/story-sessions/{story_id}/choices")
def select_choice(
    story_id: str,
    payload: StoryChoiceRequest,
    service: StorySessionService = Depends(get_story_service),
):
    return service.select_choice(story_id, payload)


@app.get("/api/v1/mock-assets/images/{asset_id}.svg")
def mock_image(asset_id: str, db: Session = Depends(get_db)) -> Response:
    asset = db.get(MediaAssetRecord, f"asset_{asset_id}")
    label = "DreamForge scene"
    if asset:
        node = db.get(StoryNodeRecord, asset.node_id)
        if node:
            label = node.title
    return Response(content=generate_mock_svg(label), media_type="image/svg+xml")


@app.get("/api/v1/mock-assets/audio/{asset_id}.wav")
def mock_audio(asset_id: str) -> Response:
    return Response(content=generate_mock_wav_bytes(), media_type="audio/wav")
