from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from raven.pricing.models import ResolvedPricingValue


class PricingValueResolutionError(ValueError):
    """Raised when pricing values cannot be resolved deterministically."""


@dataclass(frozen=True, slots=True)
class PricingValueCandidate:
    """A persisted pricing value candidate supplied to the domain resolver."""

    id: UUID
    profile_id: UUID
    key: str
    value: Decimal | str | bool
    value_type: str
    minimum_quantity: Decimal | None = None
    maximum_quantity: Decimal | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    is_active: bool = True


def resolve_pricing_values(
    candidates: tuple[PricingValueCandidate, ...],
    *,
    as_of: date,
    quantity: Decimal | None = None,
) -> tuple[ResolvedPricingValue, ...]:
    """Resolve effective pricing values into one deterministic value per key.

    Inactive, date-ineligible, and quantity-ineligible candidates are ignored.
    When multiple candidates remain for a key, the resolver prefers the most
    specific quantity range, then the most recent effective start date, and
    finally the lowest stable UUID ordering.

    This function contains no business pricing amounts or rates.
    """

    eligible = tuple(
        candidate
        for candidate in candidates
        if _is_eligible(candidate, as_of=as_of, quantity=quantity)
    )

    grouped: dict[str, list[PricingValueCandidate]] = {}
    for candidate in eligible:
        key = candidate.key.strip()
        if not key:
            raise PricingValueResolutionError("Pricing value key cannot be blank")
        grouped.setdefault(key, []).append(candidate)

    resolved: list[ResolvedPricingValue] = []
    for key, values in grouped.items():
        selected = max(values, key=_selection_key)
        resolved.append(
            ResolvedPricingValue(
                key=key,
                value=selected.value,
                source_profile_id=selected.profile_id,
            )
        )

    return tuple(sorted(resolved, key=lambda value: value.key))


def _is_eligible(
    candidate: PricingValueCandidate,
    *,
    as_of: date,
    quantity: Decimal | None,
) -> bool:
    if not candidate.is_active:
        return False

    if candidate.effective_from is not None and candidate.effective_from > as_of:
        return False
    if candidate.effective_to is not None and candidate.effective_to <= as_of:
        return False

    has_quantity_bounds = (
        candidate.minimum_quantity is not None
        or candidate.maximum_quantity is not None
    )
    if not has_quantity_bounds:
        return True
    if quantity is None:
        return False

    if (
        candidate.minimum_quantity is not None
        and quantity < candidate.minimum_quantity
    ):
        return False
    if (
        candidate.maximum_quantity is not None
        and quantity > candidate.maximum_quantity
    ):
        return False
    return True


def _selection_key(candidate: PricingValueCandidate) -> tuple[int, Decimal, date, str]:
    boundedness = int(candidate.minimum_quantity is not None) + int(
        candidate.maximum_quantity is not None
    )

    if (
        candidate.minimum_quantity is not None
        and candidate.maximum_quantity is not None
    ):
        range_width = candidate.maximum_quantity - candidate.minimum_quantity
        range_score = -range_width
    else:
        range_score = Decimal("0")

    effective_from = candidate.effective_from or date.min

    # max() is used for the business-precedence fields. UUID is inverted so
    # that the final tie-break remains stable while preferring the lowest UUID.
    return (boundedness, range_score, effective_from, _invert_uuid_hex(candidate.id.hex))


def _invert_uuid_hex(value: str) -> str:
    """Return a lexically descending-safe representation for max()."""

    return "".join(f"{15 - int(char, 16):x}" for char in value)
