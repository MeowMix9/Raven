from decimal import Decimal

import pytest

from raven.pricing.actions import (
    PricingActionValidationError,
    normalize_pricing_action,
)


def test_normalizes_percent_action() -> None:
    action = normalize_pricing_action(
        {"type": "apply_markup", "target": "unit_price", "value": "0.25"}
    )

    assert action.type == "apply_markup"
    assert action.target == "unit_price"
    assert action.value == Decimal("0.25")
    assert action.value_key is None


def test_allows_configured_value_reference() -> None:
    action = normalize_pricing_action(
        {"type": "apply_markup", "target": "unit_price", "value_key": "markup_percent"}
    )

    assert action.value is None
    assert action.value_key == "markup_percent"


def test_rejects_literal_and_configured_value_together() -> None:
    with pytest.raises(PricingActionValidationError, match="both value and value_key"):
        normalize_pricing_action(
            {
                "type": "apply_markup",
                "target": "unit_price",
                "value": "0.25",
                "value_key": "markup_percent",
            }
        )


def test_rejects_unknown_action_type() -> None:
    with pytest.raises(PricingActionValidationError, match="Unsupported pricing action type"):
        normalize_pricing_action({"type": "invent_price", "target": "unit_price", "value": 1})


def test_rejects_missing_target() -> None:
    with pytest.raises(PricingActionValidationError, match="requires a non-empty target"):
        normalize_pricing_action({"type": "apply_discount", "value": "0.10"})


def test_rejects_missing_operand() -> None:
    with pytest.raises(PricingActionValidationError, match="requires value or value_key"):
        normalize_pricing_action({"type": "multiply", "target": "unit_price"})


def test_add_charge_requires_label() -> None:
    with pytest.raises(PricingActionValidationError, match="requires a non-empty label"):
        normalize_pricing_action({"type": "add_charge", "value": "25"})


def test_add_charge_accepts_amount_and_label() -> None:
    action = normalize_pricing_action(
        {"type": "add_charge", "value": "25.00", "label": "Rush fee", "currency": "usd"}
    )

    assert action.type == "add_charge"
    assert action.value == Decimal("25.00")
    assert action.label == "Rush fee"
    assert action.currency == "USD"


def test_value_strings_that_are_not_numeric_remain_strings() -> None:
    action = normalize_pricing_action(
        {"type": "set_value", "target": "description", "value": "Contract"}
    )

    assert action.value == "Contract"


def test_invalid_currency_is_rejected() -> None:
    with pytest.raises(PricingActionValidationError, match="3-letter code"):
        normalize_pricing_action(
            {"type": "add_charge", "value": "25", "label": "Rush", "currency": "US"}
        )
