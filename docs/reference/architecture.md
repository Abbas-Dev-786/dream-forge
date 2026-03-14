# DreamForge Runtime

## Opening

`Next.js -> FastAPI -> story_crew -> PostgreSQL -> media_jobs -> worker -> assets`

The API returns the opening page immediately and stages image/audio readiness.

## Continuation

`choice click -> FastAPI -> story_crew -> new node -> media_jobs`

Only the selected path is generated.

## Crew Roles

- `planner`: opening bible + scene brief, continuation scene brief only
- `narrative`: story text, narration text, illustration prompt
- `interaction`: 2 choices or terminal state
