from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()
settings.sqlite_path.parent.mkdir(parents=True, exist_ok=True)

# check_same_thread=False: FastAPI's threadpool serves each request on a worker thread,
# so a session opened for one request can be torn down on another — SQLite's default
# same-thread guard would reject that.
engine = create_engine(
    f"sqlite:///{settings.sqlite_path}",
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Shared declarative base — ORM models (app/models/) attach here starting §1.3."""


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
