import json

from fastapi.testclient import TestClient

import dreamforge_api.api.app as api_app_module
from conftest import reset_database
from dreamforge_api.db import SessionLocal
from dreamforge_api.models import StoryNodeRecord


def test_create_story_session_returns_opening_page() -> None:
    reset_database()
    api_app_module.settings.use_mock_ai = True
    api_app_module.settings.story_crew_run_url = None
    client = TestClient(api_app_module.app)

    response = client.post(
        "/api/v1/story-sessions",
        json={
            "child_name": "Maya",
            "child_age": 8,
            "interests": ["space", "pandas"],
            "theme": "space adventure",
            "tone": "gentle",
            "language": "en",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["story_id"].startswith("st_")
    assert body["node"]["title"]
    assert body["node"]["image"]["status"] == "pending"
    assert body["node"]["audio"]["status"] == "pending"
    assert len(body["node"]["choices"]) == 2


def test_select_choice_generates_only_selected_branch() -> None:
    reset_database()
    api_app_module.settings.use_mock_ai = True
    api_app_module.settings.story_crew_run_url = None
    client = TestClient(api_app_module.app)
    opening = client.post(
        "/api/v1/story-sessions",
        json={
            "child_name": "Maya",
            "child_age": 8,
            "interests": ["space", "pandas"],
            "theme": "space adventure",
            "tone": "gentle",
            "language": "en",
        },
    ).json()

    choice_id = opening["node"]["choices"][0]["choice_id"]
    continuation = client.post(
        f"/api/v1/story-sessions/{opening['story_id']}/choices",
        json={"node_id": opening["node"]["node_id"], "choice_id": choice_id},
    )

    assert continuation.status_code == 200
    body = continuation.json()
    assert body["node"]["node_id"] != opening["node"]["node_id"]
    assert body["current_node_id"] == body["node"]["node_id"]
    assert body["node"]["story_text"]


def test_branch_memory_is_persisted_per_node() -> None:
    reset_database()
    api_app_module.settings.use_mock_ai = True
    api_app_module.settings.story_crew_run_url = None
    client = TestClient(api_app_module.app)

    opening = client.post(
        "/api/v1/story-sessions",
        json={
            "child_name": "Maya",
            "child_age": 8,
            "interests": ["space", "pandas"],
            "theme": "space adventure",
            "tone": "gentle",
            "language": "en",
        },
    ).json()

    continuation = client.post(
        f"/api/v1/story-sessions/{opening['story_id']}/choices",
        json={"node_id": opening["node"]["node_id"], "choice_id": opening["node"]["choices"][0]["choice_id"]},
    ).json()

    with SessionLocal() as db:
        opening_node = db.get(StoryNodeRecord, opening["node"]["node_id"])
        continuation_node = db.get(StoryNodeRecord, continuation["node"]["node_id"])
        assert opening_node.story_memory_json is not None
        assert continuation_node.story_memory_json is not None
        opening_memory = json.loads(opening_node.story_memory_json)
        continuation_memory = json.loads(continuation_node.story_memory_json)
        assert len(continuation_memory["branch_summaries"]) > len(opening_memory["branch_summaries"])
