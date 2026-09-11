from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest

from raven.pricing.value_resolution import (
    PricingValueCandidate,
    PricingValueResolutionError,
    resolve_pricing_values,
)


AS_OF = date(2026, 9, 11)
PROFILE_ID = UUID("00000000-0000-0000-0000-000000000001")


def candidate(
    candidate_id: str,
    key: str = "MARKUP_PERCENT",
    value: Decimal | str | bool = Decimal("25"),
    *,
    minimum_quantity: Decimal | None = None,
    maximum_quantity: Decimal | None = None,
    effective_from: date | None = None,
    effective_to: date | None = None,
    is_active: bool = True,
) -> PricingValueCandidate:
    return PricingValueCandidate(
        id=UUID(candidate_id),
        profile_id=PROFILE_ID,
        key=key,
        value=value,
        value_type="DECIMAL",
        minimum_quantity=minimum_quantity,
        maximum_quantity=maximum_quantity,
        effective_from=effective_from,
        effective_to=effective_to,
        is_active=is_active,
    )


def test_inactive_values_are_ignored() -> None:
    result = resolve_pricing_values(
        (
            candidate("00000000-0000-0000-0000-000000000010", value=Decimal("10"), is_active=False),
            candidate("00000000-0000-0000-0000-000000000020", value=Decimal("20")),
        ),
        as_of=AS_OF,
    )
    assert result[0].value == Decimal("20")


def test_future_and_expired_values_are_ignored() -> None:
    result = resolve_pricing_values(
        (
            candidate("00000000-0000-0000-0000-000000000010", value=Decimal("10"), effective_from=date(2026, 9, 12)),
            candidate("00000000-0000-0000-0000-000000000020", value=Decimal("20"), effective_to=date(2026, 9, 11)),
            candidate("00000000-0000-0000-0000-000000000030", value=Decimal("30")),
        ),
        as_of=AS_OF,
    )
    assert result[0].value == Decimal("30")


def test_quantity_bounded_value_beats_unbounded_default() -> None:
    result = resolve_pricing_values(
        (
            candidate("00000000-0000-0000-0000-000000000010", value=Decimal("10")),
            candidate(
                "00000000-0000-0000-0000-000000000020",
                value=Decimal("20"),
                minimum_quantity=Decimal("100"),
                maximum_quantity=Decimal("199"),
            ),
        ),
        as_of=AS_OF,
        quantity=Decimal("150"),
    )
    assert result[0].value == Decimal("20")


def test_narrower_overlapping_quantity_range_wins() -> None:
    result = resolve_pricing_values(
        (
            candidate(
                "00000000-0000-0000-0000-000000000010",
                value=Decimal("10"),
                minimum_quantity=Decimal("100"),
                maximum_quantity=Decimal("300"),
            ),
            candidate(
                "00000000-0000-0000-0000-000000000020",
                value=Decimal("20"),
                minimum_quantity=Decimal("150"),
                maximum_quantity=Decimal("200"),
            ),
        ),
        as_of=AS_OF,
        quantity=Decimal("175"),
    )
    assert result[0].value == Decimal("20")


@pytest.mark.parametrize("quantity", [Decimal("100"), Decimal("199")])
def test_quantity_bounds_are_inclusive(quantity: Decimal) -> None:
    result = resolve_pricing_values(
        (
            candidate(
                "00000000-0000-0000-0000-000000000010",
                minimum_quantity=Decimal("100"),
                maximum_quantity=Decimal("199"),
            ),
        ),
        as_of=AS_OF,
        quantity=quantity,
    )
    assert result[0].value == Decimal("25")


def test_bounded_value_is_ignored_when_quantity_is_omitted() -> None:
    result = resolve_pricing_values(
        (
            candidate("00000000-0000-0000-0000-000000000010", value=Decimal("10")),
            candidate(
                "00000000-0000-0000-0000-000000000020",
                value=Decimal("20"),
                minimum_quantity=Decimal("100"),
            ),
        ),
        as_of=AS_OF,
    )
    assert result[0].value == Decimal("10")


def test_latest_effective_value_wins_when_specificity_is_equal() -> None:
    result = resolve_pricing_values(
        (
            candidate("00000000-0000-0000-0000-000000000010", value=Decimal("10"), effective_from=date(2026, 1, 1)),
            candidate("00000000-0000-0000-0000-000000000020", value=Decimal("20"), effective_from=date(2026, 8, 1)),
        ),
        as_of=AS_OF,
    )
    assert result[0].value == Decimal("20")


def test_uuid_tie_break_is_deterministic_and_prefers_lowest_uuid() -> None:
    first = candidate("00000000-0000-0000-0000-000000000010", value=Decimal("10"))
    second = candidate("00000000-0000-0000-0000-000000000020", value=Decimal("20"))

    forward = resolve_pricing_values((first, second), as_of=AS_OF)
    reversed_order = resolve_pricing_values((second, first), as_of=AS_OF)

    assert forward == reversed_order
    assert forward[0].value == Decimal("10")


def test_multiple_keys_are_returned_in_stable_key_order() -> None:
    result = resolve_pricing_values(
        (
            candidate("00000000-0000-0000-0000-000000000010", key="Z_KEY", value="z"),
            candidate("00000000-0000-0000-0000-000000000020", key="A_KEY", value="a"),
        ),
        as_of=AS_OF,
    )
    assert [item.key for item in result] == ["A_KEY", "Z_KEY"]


def test_blank_key_raises_clear_error() -> None:
    with pytest.raises(PricingValueResolutionError, match="key cannot be blank"):
        resolve_pricing_values(
            (candidate("00000000-0000-0000-0000-000000000010", key="   "),),
            as_of=AS_OF,
        )
