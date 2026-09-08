import uuid
from datetime import datetime, timezone

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    filename: Mapped[str] = mapped_column(String)
    # "order" is a reserved word in SQL — order_index sidesteps quoting footguns;
    # AssetResponse.order maps to this field at the API layer.
    order_index: Mapped[int] = mapped_column(Integer)
    # Populated once §1.3 upload logic lands (R2 object key). Source files are deleted
    # after processing per CLAUDE.md — this column tracks where, not permanent storage.
    storage_key: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
