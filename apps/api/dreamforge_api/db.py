from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

from dreamforge_api.config import get_settings


Base = declarative_base()


def _engine_kwargs(database_url: str) -> dict[str, object]:
    if database_url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    return {}


settings = get_settings()
engine = create_engine(settings.database_url, future=True, **_engine_kwargs(settings.database_url))
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    import dreamforge_api.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_runtime_columns()


def _ensure_runtime_columns() -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if "story_nodes" not in table_names:
        return
    column_names = {column["name"] for column in inspector.get_columns("story_nodes")}
    if "story_memory_json" not in column_names:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE story_nodes ADD COLUMN story_memory_json TEXT"))
