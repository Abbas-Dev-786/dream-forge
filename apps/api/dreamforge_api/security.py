from fastapi import HTTPException, status


BANNED_TERMS = {
    "blood",
    "gore",
    "murder",
    "kill",
    "terror",
    "horror",
    "romance",
    "nsfw",
    "weapon",
    "gun",
}


def assert_safe_prompt(parts: list[str]) -> None:
    lowered = " ".join(parts).lower()
    for term in BANNED_TERMS:
        if term in lowered:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"DreamForge cannot generate stories with unsafe theme content: {term}.",
            )

