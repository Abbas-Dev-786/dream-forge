# DreamForge

DreamForge is a DigitalOcean-native storytelling demo for kids. This restart keeps the product lean:

- `apps/web`: Next.js story creation and reading experience
- `apps/api`: FastAPI API, persistence, and media job orchestration
- `apps/worker`: media worker for image and narration jobs
- `agents/story_crew`: one ADK LangGraph crew with planner, narrative, and interaction roles
- `docs/reference`: deployment and setup notes

## Local Development

### API

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
uvicorn apps.api.main:app --reload --port 8000
```

### Worker

```bash
source .venv/bin/activate
python -m apps.worker.main
```

### Web

```bash
pnpm install
pnpm dev:web
```

### ADK Crew

```bash
cd agents/story_crew
gradient agent configure --no-interactive --agent-workspace-name dreamforge-story-crew --deployment-name development --entrypoint-file main.py
gradient agent run
```

## Runtime Notes

- `DREAMFORGE_USE_MOCK_AI=true` keeps the full stack runnable without deployed ADK or inference services.
- The API returns story text immediately and stages media readiness.
- The worker uses a simple `status + attempt_count + max_attempts` model with up to 3 retries.
