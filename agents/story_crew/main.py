from __future__ import annotations

from gradient_adk import entrypoint

from crew import StoryCrewRuntime


runtime = StoryCrewRuntime()


@entrypoint
def main(payload: dict, context: dict) -> dict[str, object]:
    prompt = payload.get("prompt", {})
    if not isinstance(prompt, dict):
        raise ValueError("DreamForge story crew expects the `prompt` field to be a JSON object.")
    return {"response": runtime.run(prompt)}
