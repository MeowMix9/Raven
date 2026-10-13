import pytest
from pydantic import ValidationError

from raven.api.inventory import InventoryImport, InventoryRecord, apply_client_policy


class Client:
    minimum_quantity_available = 3


def test_inventory_record_keeps_public_json_fields() -> None:
    record = InventoryRecord(
        sku="FM-001",
        quantity_available=7,
        unit_price="12.50",
        map_price="15.00",
        product_title="Example Shirt",
        image_url="https://example.com/image.jpg",
    )
    data = record.model_dump(mode="json")

    assert data["sku"] == "FM-001"
    assert data["quantity_available"] == 7
    assert data["unit_price"] == 12.5
    assert data["map_price"] == 15.0


def test_import_rejects_duplicate_skus_case_insensitively() -> None:
    with pytest.raises(ValidationError):
        InventoryImport(items=[InventoryRecord(sku="FM-001"), InventoryRecord(sku="fm-001")])


def test_client_quantity_policy_hides_items_below_threshold() -> None:
    items = [
        {"sku": "A", "quantity_available": 2},
        {"sku": "B", "quantity_available": 3},
        {"sku": "C", "quantity_available": None},
    ]

    assert [item["sku"] for item in apply_client_policy(items, Client())] == ["B"]


def test_no_client_threshold_returns_all_items() -> None:
    class UnrestrictedClient:
        minimum_quantity_available = None

    items = [{"sku": "A", "quantity_available": 0}]
    assert apply_client_policy(items, UnrestrictedClient()) == items
