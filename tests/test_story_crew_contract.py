import copy
import os
import sys
from pathlib import Path


AGENT_DIR = Path(__file__).resolve().parents[1] / "agents" / "story_crew"
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))

from crew import StoryCrewRuntime  # noqa: E402


def test_story_crew_opening_and_continuation_contracts() -> None:
    os.environ["DREAMFORGE_USE_MOCK_AI"] = "true"
    runtime = StoryCrewRuntime()
    opening_payload = {
        "mode": "create_opening_scene",
        "child_profile": {"name": "Maya", "age": 8, "interests": ["space", "pandas"]},
        "story_request": {"theme": "space adventure", "tone": "gentle"},
        "constraints": {"max_branch_depth": 2, "max_total_nodes": 7, "language": "en"},
    }

    opening = runtime.run(opening_payload)
    assert "story_bible" in opening
    assert len(opening["choices"]) == 2

    original_bible = copy.deepcopy(opening["story_bible"])
    continuation = runtime.run(
        {
            "mode": "continue_story_from_choice",
            "story_bible": original_bible,
            "current_node": {
                "node_id": "node_1",
                "title": opening["scene_brief"]["title"],
                "scene_summary": opening["scene_brief"]["scene_summary"],
            },
            "selected_choice": opening["choices"][0],
            "constraints": {"current_depth": 1, "max_branch_depth": 2, "remaining_node_budget": 6},
        }
    )

    assert "story_bible" not in continuation
    assert continuation["scene_brief"]["branch_depth"] == 1
    assert len(continuation["choices"]) == 2
    assert original_bible == opening["story_bible"]
