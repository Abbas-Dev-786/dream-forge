from __future__ import annotations

import time

from dreamforge_api.config import get_settings
from dreamforge_api.db import SessionLocal, init_db
from dreamforge_api.services.media_jobs import MediaJobService


def main() -> None:
    settings = get_settings()
    if settings.auto_migrate:
        init_db()

    while True:
        with SessionLocal() as db:
            service = MediaJobService(db, settings)
            processed = service.process_next_job()
        if not processed:
            time.sleep(settings.worker_loop_interval_seconds)


if __name__ == "__main__":
    main()
