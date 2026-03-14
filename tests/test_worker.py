from dreamforge_api.config import Settings
from dreamforge_api.config import get_settings
from dreamforge_api.db import SessionLocal
from dreamforge_api.models import StoryNodeRecord
from dreamforge_api.services.media_jobs import MediaJobService
from dreamforge_api.services.story_sessions import StorySessionService
from dreamforge_api.schemas import StorySessionCreateRequest, Tone
from conftest import reset_database


def test_worker_moves_mock_jobs_to_ready() -> None:
    reset_database()
    base = get_settings()
    settings = Settings(
        use_mock_ai=True,
        database_url=base.database_url,
        app_public_base_url=base.app_public_base_url,
        worker_loop_interval_seconds=base.worker_loop_interval_seconds,
    )

    with SessionLocal() as db:
        service = StorySessionService(db, settings)
        created = service.create_story_session(
            StorySessionCreateRequest(
                child_name="Maya",
                child_age=8,
                interests=["space", "pandas"],
                theme="space adventure",
                tone=Tone.GENTLE,
                language="en",
            )
        )

    with SessionLocal() as db:
        worker = MediaJobService(db, settings)
        while worker.process_next_job():
            pass

    with SessionLocal() as db:
        node = db.get(StoryNodeRecord, created.node.node_id)
        assert node.image_status == "ready"
        assert node.audio_status == "ready"
        assert node.image_url.endswith(".svg")
        assert node.audio_url.endswith(".wav")
