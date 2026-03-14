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
    assert "story_memory" in opening
    assert len(opening["choices"]) == 2
    assert " in " in opening["illustration_prompt"]
    assert opening["illustration_prompt"].count(",") >= 2

    original_bible = copy.deepcopy(opening["story_bible"])
    continuation = runtime.run(
        {
            "mode": "continue_story_from_choice",
            "story_bible": original_bible,
            "story_memory": opening["story_memory"],
            "current_node": {
                "node_id": "node_1",
                "title": opening["scene_brief"]["title"],
                "scene_summary": opening["scene_brief"]["scene_summary"],
            },
            "selected_choice": opening["choices"][0],
            "tone": "gentle",
            "constraints": {"current_depth": 1, "max_branch_depth": 3, "remaining_node_budget": 6},
        }
    )

    assert "story_bible" not in continuation
    assert continuation["scene_brief"]["branch_depth"] == 1
    assert len(continuation["choices"]) == 2
    assert len(continuation["story_memory"]["branch_summaries"]) > len(opening["story_memory"]["branch_summaries"])
    assert original_bible == opening["story_bible"]


def test_reviewer_rewrites_scary_mock_scene_for_young_reader() -> None:
    os.environ["DREAMFORGE_USE_MOCK_AI"] = "true"
    runtime = StoryCrewRuntime()
    state = runtime.graph.invoke(
        {
            "request": {
                "mode": "create_opening_scene",
                "child_profile": {"name": "Milo", "age": 5, "interests": ["lanterns", "clouds"]},
                "story_request": {"theme": "shadow parade", "tone": "gentle"},
                "constraints": {"max_branch_depth": 2, "max_total_nodes": 7, "language": "en"},
            },
            "review_attempts": 0,
            "critique": "",
        }
    )

    assert state["review_attempts"] == 1
    assert "shadow" not in state["output"]["story_text"].lower()
    assert "glowing lantern" in state["output"]["story_text"].lower()


def test_story_memory_grows_across_multiple_branch_steps() -> None:
    os.environ["DREAMFORGE_USE_MOCK_AI"] = "true"
    runtime = StoryCrewRuntime()
    opening = runtime.run(
        {
            "mode": "create_opening_scene",
            "child_profile": {"name": "Maya", "age": 8, "interests": ["space", "pandas"]},
            "story_request": {"theme": "space adventure", "tone": "gentle"},
            "constraints": {"max_branch_depth": 4, "max_total_nodes": 7, "language": "en"},
        }
    )

    memory = opening["story_memory"]
    current_node = opening["scene_brief"]
    for depth in range(1, 4):
        continuation = runtime.run(
            {
                "mode": "continue_story_from_choice",
                "story_bible": opening["story_bible"],
                "story_memory": memory,
                "current_node": {
                    "node_id": f"node_{depth}",
                    "title": current_node["title"],
                    "scene_summary": current_node["scene_summary"],
                },
                "selected_choice": {"choice_id": "A", "label": f"Follow the singing lantern trail at turn {depth}"},
                "tone": "gentle",
                "constraints": {"current_depth": depth, "max_branch_depth": 4, "remaining_node_budget": 7 - depth},
            }
        )
        memory = continuation["story_memory"]
        current_node = continuation["scene_brief"]

    assert len(memory["branch_summaries"]) == 4
