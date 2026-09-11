from decimal import Decimal
from uuid import uuid4

import pytest

from raven.infrastructure.quotes.repository import _resolve_item_prices
from raven.quotes.models import QuoteItem


def _item(*, unit_price=None, extended_price=None) -> QuoteItem:
    return QuoteItem(
        line_number=1,
        product_id=uuid4(),
        description="Test product",
        quantity=Decimal("10"),
        unit_of_measure="EA",
        unit_cost=Decimal("5.00"),
        extended_cost=Decimal("50.00"),
        unit_price=unit_price,
        extended_price=extended_price,
    )


def test_draft_item_without_sell_price_falls_back_to_cost() -> None:
    assert _resolve_item_prices(_item(), calculated=False) == (
        Decimal("5.00"),
        Decimal("50.00"),
    )


def test_explicit_sell_price_is_preserved() -> None:
    assert _resolve_item_prices(
        _item(unit_price=Decimal("7.50"), extended_price=Decimal("75.00")),
        calculated=False,
    ) == (Decimal("7.50"), Decimal("75.00"))


def test_calculated_item_requires_explicit_sell_price() -> None:
    with pytest.raises(ValueError, match="requires explicit unit_price"):
        _resolve_item_prices(_item(), calculated=True)


def test_calculated_item_preserves_explicit_sell_price() -> None:
    assert _resolve_item_prices(
        _item(unit_price=Decimal("7.50"), extended_price=Decimal("75.00")),
        calculated=True,
    ) == (Decimal("7.50"), Decimal("75.00"))
