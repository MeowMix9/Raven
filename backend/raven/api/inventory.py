from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from hashlib import sha256
import hmac
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_serializer, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from raven.core.config import get_settings
from raven.database.session import get_session_factory
from raven.infrastructure.models.inventory import InventoryApiClient, InventorySnapshot

router = APIRouter(prefix="/api/v1/inventory", tags=["inventory"])


class InventoryRecord(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    sku: str = Field(min_length=1, max_length=128)
    show: str = ""
    item: str = ""
    description: str = ""
    quantity_available: int | None = Field(default=None, ge=0)
    unit_price: Decimal | None = Field(default=None, ge=0)
    map_price: Decimal | None = Field(default=None, ge=0)
    product_title: str = ""
    variant_title: str = ""
    image_url: str = ""

    @field_serializer("unit_price", "map_price")
    def serialize_prices(self, value: Decimal | None) -> float | None:
        return float(value) if value is not None else None


class InventoryImport(BaseModel):
    source: str = Field(default="forward_merch", min_length=1, max_length=100)
    items: list[InventoryRecord] = Field(min_length=1, max_length=100000)

    @model_validator(mode="after")
    def reject_duplicate_skus(self) -> "InventoryImport":
        skus = [item.sku.casefold() for item in self.items]
        if len(skus) != len(set(skus)):
            raise ValueError("Inventory import contains duplicate SKUs")
        return self


def get_db():
    factory = get_session_factory()
    with factory() as session:
        yield session


def hash_api_key(raw_key: str) -> str:
    return sha256(raw_key.encode("utf-8")).hexdigest()


def require_ingest_key(
    x_raven_ingest_key: Annotated[str | None, Header()] = None,
) -> None:
    expected = get_settings().inventory_ingest_key
    if not expected:
        raise HTTPException(status_code=503, detail="Inventory ingestion is not configured")
    if not x_raven_ingest_key or not hmac.compare_digest(x_raven_ingest_key, expected):
        raise HTTPException(status_code=401, detail="Invalid ingestion credential")


def get_current_client(
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
) -> InventoryApiClient:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Bearer API key required")
    raw_key = authorization.removeprefix("Bearer ").strip()
    if not raw_key:
        raise HTTPException(status_code=401, detail="Bearer API key required")

    client = db.scalar(
        select(InventoryApiClient).where(
            InventoryApiClient.api_key_hash == hash_api_key(raw_key),
            InventoryApiClient.is_active.is_(True),
        )
    )
    if client is None:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return client


def get_latest_snapshot(db: Session) -> InventorySnapshot:
    snapshot = db.scalar(
        select(InventorySnapshot).order_by(InventorySnapshot.created_at.desc()).limit(1)
    )
    if snapshot is None:
        raise HTTPException(status_code=503, detail="No inventory snapshot has been imported")
    return snapshot


def apply_client_policy(
    items: list[dict[str, Any]], client: InventoryApiClient
) -> list[dict[str, Any]]:
    threshold = client.minimum_quantity_available
    if threshold is None:
        return items
    return [
        item
        for item in items
        if item.get("quantity_available") is not None
        and item["quantity_available"] >= threshold
    ]


def snapshot_metadata(snapshot: InventorySnapshot) -> dict[str, Any]:
    return {
        "id": str(snapshot.id),
        "source": snapshot.source,
        "row_count": snapshot.row_count,
        "imported_at": snapshot.created_at.isoformat(),
    }


@router.post("/import", status_code=201)
def import_inventory(
    payload: InventoryImport,
    _: Annotated[None, Depends(require_ingest_key)],
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    items = [item.model_dump(mode="json") for item in payload.items]
    snapshot = InventorySnapshot(
        source=payload.source,
        row_count=len(items),
        items_json=items,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return {"status": "imported", "snapshot": snapshot_metadata(snapshot)}


@router.get("")
def list_inventory(
    client: Annotated[InventoryApiClient, Depends(get_current_client)],
    db: Session = Depends(get_db),
    q: str | None = Query(default=None, min_length=1, max_length=200),
    sku_prefix: str | None = Query(default=None, min_length=1, max_length=128),
    available_only: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    snapshot = get_latest_snapshot(db)
    items = apply_client_policy(snapshot.items_json, client)

    if q:
        needle = q.casefold()
        items = [
            item for item in items
            if needle in str(item.get("sku", "")).casefold()
            or needle in str(item.get("description", "")).casefold()
            or needle in str(item.get("product_title", "")).casefold()
        ]
    if sku_prefix:
        prefix = sku_prefix.casefold()
        items = [item for item in items if str(item.get("sku", "")).casefold().startswith(prefix)]
    if available_only:
        items = [
            item for item in items
            if item.get("quantity_available") is not None
            and item["quantity_available"] > 0
        ]

    total = len(items)
    start = (page - 1) * page_size
    return {
        "data": items[start:start + page_size],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "pages": (total + page_size - 1) // page_size,
        },
        "snapshot": snapshot_metadata(snapshot),
    }


@router.get("/{sku}")
def get_inventory_item(
    sku: str,
    client: Annotated[InventoryApiClient, Depends(get_current_client)],
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    snapshot = get_latest_snapshot(db)
    visible_items = apply_client_policy(snapshot.items_json, client)
    item = next(
        (row for row in visible_items if str(row.get("sku", "")).casefold() == sku.casefold()),
        None,
    )
    if item is None:
        # Do not reveal whether a hidden SKU exists.
        raise HTTPException(status_code=404, detail="Inventory item not found")
    return {"data": item, "snapshot": snapshot_metadata(snapshot)}
