from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any


SUPPORTED_ACTION_TYPES = frozenset(
    {
        "set_value",
        "add_amount",
        "subtract_amount",
        "multiply",
        "add_percent",
        "subtract_percent",
        "apply_markup",
        "apply_discount",
        "add_charge",
        "set_minimum",
    }
)

VALUE_REQUIRED_TYPES = frozenset(
    {
        "set_value",
        "add_amount",
        "subtract_amount",
        "multiply",
        "add_percent",
        "subtract_percent",
        "apply_markup",
        "apply_discount",
        "set_minimum",
    }
)

TARGET_REQUIRED_TYPES = frozenset(
    {
        "set_value",
        "add_amount",
        "subtract_amount",
        "multiply",
        "add_percent",
        "subtract_percent",
        "apply_markup",
        "apply_discount",
        "set_minimum",
    }
)


class PricingActionValidationError(ValueError):
    """Raised when a configured pricing action violates the action contract."""


@dataclass(frozen=True, slots=True)
class PricingAction:
    """Normalized, validated pricing action.

    Percent values use decimal ratios: 0.25 means 25%, not 0.25%.
    ``value_key`` allows the calculation pipeline to resolve an operand from
    a configured PricingValue instead of embedding a business constant.
    """

    type: str
    target: str | None
    value: Decimal | str | bool | None
    value_key: str | None
    label: str | None
    currency: str | None


def normalize_pricing_action(action: dict[str, Any]) -> PricingAction:
    if not isinstance(action, dict) or not action:
        raise PricingActionValidationError("Rule action must be a non-empty object")

    action_type = action.get("type")
    if not isinstance(action_type, str) or not action_type.strip():
        raise PricingActionValidationError("Rule action type must be a non-empty string")
    action_type = action_type.strip().lower()

    if action_type not in SUPPORTED_ACTION_TYPES:
        raise PricingActionValidationError(f"Unsupported pricing action type: {action_type}")

    target = action.get("target")
    if action_type in TARGET_REQUIRED_TYPES:
        if not isinstance(target, str) or not target.strip():
            raise PricingActionValidationError(
                f"Pricing action '{action_type}' requires a non-empty target"
            )
        target = target.strip()
    elif target is not None and (not isinstance(target, str) or not target.strip()):
        raise PricingActionValidationError("Pricing action target must be a non-empty string")

    value_key = action.get("value_key")
    if value_key is not None:
        if not isinstance(value_key, str) or not value_key.strip():
            raise PricingActionValidationError("Pricing action value_key must be a non-empty string")
        value_key = value_key.strip()

    has_value = "value" in action and action["value"] is not None
    if action_type in VALUE_REQUIRED_TYPES and not has_value and value_key is None:
        raise PricingActionValidationError(
            f"Pricing action '{action_type}' requires value or value_key"
        )
    if has_value and value_key is not None:
        raise PricingActionValidationError("Pricing action cannot define both value and value_key")

    value = _normalize_value(action.get("value")) if has_value else None

    if action_type == "add_charge":
        label = action.get("label")
        if not isinstance(label, str) or not label.strip():
            raise PricingActionValidationError("Pricing action 'add_charge' requires a non-empty label")
        label = label.strip()
    else:
        label = action.get("label")
        if label is not None and (not isinstance(label, str) or not label.strip()):
            raise PricingActionValidationError("Pricing action label must be a non-empty string")
        label = label.strip() if isinstance(label, str) else None

    currency = action.get("currency")
    if currency is not None:
        if not isinstance(currency, str) or len(currency.strip()) != 3:
            raise PricingActionValidationError("Pricing action currency must be a 3-letter code")
        currency = currency.strip().upper()

    return PricingAction(
        type=action_type,
        target=target,
        value=value,
        value_key=value_key,
        label=label,
        currency=currency,
    )


def _normalize_value(value: Any) -> Decimal | str | bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, str):
        try:
            return Decimal(value)
        except InvalidOperation:
            return value
    if value is None:
        raise PricingActionValidationError("Pricing action value cannot be null")
    raise PricingActionValidationError("Pricing action value must be decimal, string, or boolean")
