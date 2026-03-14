# DigitalOcean Setup Notes

## ADK Crew

Run these commands from `agents/story_crew`:

```bash
gradient agent configure --no-interactive --agent-workspace-name dreamforge-story-crew --deployment-name development --entrypoint-file main.py
gradient agent run
gradient agent deploy
```

The crew expects:

- `GRADIENT_MODEL_ACCESS_KEY`
- `DIGITALOCEAN_API_TOKEN` for deploys
- `STORY_CREW_MODEL_ID`
- `INFERENCE_BASE_URL`

## API / Worker

The API and worker read root `.env` values for:

- `DATABASE_URL`
- `STORY_CREW_RUN_URL`
- `GRADIENT_MODEL_ACCESS_KEY`
- `SPACES_*`
- `APP_PUBLIC_BASE_URL`
