from sqlalchemy import Boolean, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from raven.infrastructure.models.base import TimestampedModel


class InventorySnapshot(TimestampedModel):
    """Immutable imported inventory snapshot; the newest snapshot is the current feed."""

    __tablename__ = "inventory_snapshots"

    source: Mapped[str] = mapped_column(String(100), nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False)
    items_json: Mapped[list[dict]] = mapped_column(JSONB, nullable=False)


class InventoryApiClient(TimestampedModel):
    """Client access and visibility policy. Only a hash of the API key is stored."""

    __tablename__ = "inventory_api_clients"

    client_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    api_key_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    minimum_quantity_available: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
