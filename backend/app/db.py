import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

DEFAULT_DATABASE_URL = "postgresql+psycopg2://calm:calm@db:5432/calm"


def normalize_database_url(url: str) -> str:
    """Accept the connection strings hosters hand out.

    Render/Heroku style URLs start with ``postgres://`` which SQLAlchemy 2 no
    longer understands, and plain ``postgresql://`` should use the psycopg2
    driver that is pinned in requirements.txt.
    """
    if url.startswith("postgres://"):
        return "postgresql+psycopg2://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg2://" + url[len("postgresql://") :]
    return url


DATABASE_URL = normalize_database_url(os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL))

_engine_kwargs: dict[str, object] = {"pool_pre_ping": True}
if DATABASE_URL.startswith("postgresql"):
    # Managed Postgres (Neon, Render, ...) drops idle connections; recycling
    # before that keeps requests from failing after quiet periods.
    _engine_kwargs.update(pool_recycle=300, pool_size=5, max_overflow=5)

engine = create_engine(DATABASE_URL, **_engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
