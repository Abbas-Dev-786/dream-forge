from __future__ import annotations

import json

from schemas import SceneBrief, StoryBible, StoryMemory


def age_band(age: int) -> str:
    if age <= 7:
        return "5-7"
    if age <= 10:
        return "8-10"
    return "11-14"


def reading_guidance(age: int) -> str:
    band = age_band(age)
    if band == "5-7":
        return "Use short sentences, concrete nouns, and comforting sensory details."
    if band == "8-10":
        return "Use vivid but clear prose, gentle suspense, and emotionally direct language."
    return "Use richer imagery while keeping the story warm, clear, and age-safe."


def planner_opening_prompt() -> str:
    return (
        "You are the planner for DreamForge, an interactive children's story crew. "
        "Create a magical but grounded opening story world for one child hero. "
        "Return JSON only with keys story_bible and scene_brief. "
        "Story bible rules: keep hero, world rules, and visual style stable across the story. "
        "Scene brief rules: one opening scene, concrete setting, active hero, no fear-based hook."
    )


def planner_continuation_prompt() -> str:
    return (
        "You are the continuation planner for DreamForge. "
        "The story_bible is canonical and immutable. Do not rewrite it. "
        "Use story_memory plus the selected choice to plan the next scene_brief. "
        "Return JSON only with key scene_brief. "
        "The next scene must respect prior branch events, preserve tone, and keep the hero active."
    )


def planner_opening_example_input() -> dict[str, object]:
    return {
        "mode": "create_opening_scene",
        "child_profile": {"name": "Maya", "age": 8, "interests": ["space", "pandas"]},
        "story_request": {"theme": "space adventure", "tone": "gentle"},
        "constraints": {"max_branch_depth": 2, "max_total_nodes": 7, "language": "en"},
    }


def planner_opening_example_output() -> dict[str, object]:
    return {
        "story_bible": {
            "hero_profile": {
                "name": "Maya",
                "age": 8,
                "appearance": "Maya, a curious child in a silver scarf with a glowing star-map satchel",
                "traits": ["curious", "kind", "brave"],
            },
            "world_rules": {
                "setting": "a warm sky-port where star doors open above floating gardens",
                "magic_system": "gentle starlight responds to kind choices and patient courage",
                "safety_constraints": ["no horror", "no violence", "no romance"],
            },
            "visual_style": {
                "look": "storybook adventure illustration",
                "palette": "bright pastels with sunset gold and sky blue",
                "lighting": "warm cinematic glow",
            },
            "continuity_facts": [
                "Maya always carries the glowing star-map satchel.",
                "The world reacts kindly when Maya makes generous choices.",
            ],
        },
        "scene_brief": {
            "title": "The First Star Door",
            "scene_summary": "Maya notices a glowing star door above the floating garden bridge and steps closer to discover where it leads.",
            "branch_depth": 0,
        },
    }


def planner_continuation_example_output() -> dict[str, object]:
    return {
        "scene_brief": {
            "title": "The Lantern River",
            "scene_summary": "Maya follows the singing lantern trail to a calm river of light where a new clue waits in the reeds.",
            "branch_depth": 1,
        }
    }


def narrative_prompt(story_bible: StoryBible, scene_brief: SceneBrief, tone: str, story_memory: StoryMemory, critique: str = "") -> str:
    age = story_bible.hero_profile.age
    constraints = ", ".join(story_bible.world_rules.safety_constraints)
    memory_text = "; ".join(story_memory.branch_summaries[-4:]) or "No prior branch events yet."
    critique_line = f"Rewrite critique to address: {critique}. " if critique else ""
    return (
        "You are an award-winning children's author specializing in interactive adventures. "
        f"The hero is {story_bible.hero_profile.name}, age {age}. "
        f"Tone: {tone}. Reading level guidance: {reading_guidance(age)} "
        f"World setting: {story_bible.world_rules.setting}. "
        f"Hero appearance must remain stable: {story_bible.hero_profile.appearance}. "
        f"Recent branch memory: {memory_text}. "
        f"Critical constraints: {constraints}. "
        "Keep the hero active, make the language warm and vivid, and avoid repetition. "
        "Return JSON only with keys story_text, narration_text, illustration_prompt. "
        "narration_text should match story_text closely with only tiny pronunciation cleanup. "
        "illustration_prompt must follow this exact formula: "
        "[Subject description] in [Environment description], [Lighting], [Visual style]. "
        f"{critique_line}"
    )


def narrative_example_input(story_bible: StoryBible, scene_brief: SceneBrief, tone: str) -> dict[str, object]:
    return {
        "story_bible": story_bible.model_dump(mode="json"),
        "scene_brief": scene_brief.model_dump(mode="json"),
        "tone": tone,
        "story_memory": {"branch_summaries": ["Maya first discovered the star door above the floating garden bridge."]},
    }


def narrative_example_output(story_bible: StoryBible) -> dict[str, object]:
    return {
        "story_text": (
            f"{story_bible.hero_profile.name} lifted the glowing satchel and listened as the lanterns began to hum. "
            "The path ahead felt exciting instead of scary, and each step made the air sparkle with friendly light."
        ),
        "narration_text": (
            f"{story_bible.hero_profile.name} lifted the glowing satchel and listened as the lanterns began to hum. "
            "The path ahead felt exciting instead of scary, and each step made the air sparkle with friendly light."
        ),
        "illustration_prompt": (
            f"{story_bible.hero_profile.appearance} in a glowing lantern path beside a calm river of light, "
            f"{story_bible.visual_style.lighting}, {story_bible.visual_style.look} with {story_bible.visual_style.palette}"
        ),
    }


def interaction_prompt(story_bible: StoryBible, scene_brief: SceneBrief, tone: str, story_memory: StoryMemory) -> str:
    memory_text = "; ".join(story_memory.branch_summaries[-4:]) or "No prior branch events yet."
    return (
        "You design branching choices for a children's interactive story. "
        f"Tone: {tone}. Hero: {story_bible.hero_profile.name}. "
        f"Scene: {scene_brief.scene_summary}. "
        f"Recent branch memory: {memory_text}. "
        "Return JSON only with keys choices and is_terminal. "
        "For non-terminal scenes return exactly 2 distinct, meaningful, child-safe choices. "
        "The choices must lead to different kinds of next scenes and must not repeat the same wording."
    )


def interaction_example_output() -> dict[str, object]:
    return {
        "choices": [
            {"choice_id": "A", "label": "Follow the singing lantern trail"},
            {"choice_id": "B", "label": "Knock on the moonlit gate"},
        ],
        "is_terminal": False,
    }


def reviewer_prompt(story_bible: StoryBible, tone: str, story_text: str, narration_text: str) -> str:
    age = story_bible.hero_profile.age
    constraints = ", ".join(story_bible.world_rules.safety_constraints)
    return (
        "You are a safety and age-fit reviewer for children's stories. "
        f"Reader age: {age}. Tone target: {tone}. "
        f"Safety constraints: {constraints}. "
        "Judge whether the story_text and narration_text are warm, child-safe, age-appropriate, and tonally consistent. "
        "Reject scary imagery, implied danger, or vocabulary too mature for the target age. "
        "Return JSON only with keys approved, critique, severity. "
        "If approved, keep critique short. If rejected, critique must tell the writer exactly what to soften or rewrite."
    )


def reviewer_example_output(approved: bool) -> dict[str, object]:
    if approved:
        return {"approved": True, "critique": "The scene is warm, clear, and age-safe.", "severity": "low"}
    return {
        "approved": False,
        "critique": "The dark shadow imagery feels scary for a 5-year-old. Rewrite the scene to feel welcoming and gently magical.",
        "severity": "high",
    }


def memory_prompt(story_bible: StoryBible, scene_brief: SceneBrief, story_memory: StoryMemory, selected_choice: str | None) -> str:
    age = story_bible.hero_profile.age
    memory_text = "; ".join(story_memory.branch_summaries[-4:]) or "No prior branch events yet."
    choice_text = selected_choice or "Opening scene"
    return (
        "You maintain branch memory for an interactive children's story. "
        f"Reader age: {age}. "
        f"Recent memory: {memory_text}. "
        f"Current scene: {scene_brief.scene_summary}. "
        f"Triggering choice: {choice_text}. "
        "Return JSON only with key memory_entry. "
        "Write one short factual memory line that will help future scenes stay consistent. "
        "Keep it concrete, child-safe, and branch-specific."
    )


def memory_example_output() -> dict[str, object]:
    return {
        "memory_entry": "Maya followed the singing lantern trail and discovered that the calm river of light hides friendly clues in the reeds."
    }


def json_message(content: dict[str, object]) -> str:
    return json.dumps(content, ensure_ascii=True)
