from datetime import date
from uuid import UUID

import pytest

from raven.pricing.profile_selection import (
    PricingProfileCandidate,
    PricingProfileSelectionError,
    select_pricing_profile,
)


AS_OF = date(2026, 9, 11)
CUSTOMER_ID = UUID("00000000-0000-0000-0000-000000000001")
PRODUCT_ID = UUID("00000000-0000-0000-0000-000000000002")


def candidate(
    profile_id: str,
    *,
    scope_type: str = "DEFAULT",
    scope_id: UUID | None = None,
    assignment_priority: int = 0,
    profile_priority: int = 0,
    assignment_effective_from: date | None = None,
    assignment_effective_to: date | None = None,
    profile_effective_from: date | None = None,
    profile_effective_to: date | None = None,
    profile_version: int = 1,
    assignment_is_active: bool = True,
    profile_is_active: bool = True,
) -> PricingProfileCandidate:
    return PricingProfileCandidate(
        profile_id=UUID(profile_id),
        scope_type=scope_type,
        scope_id=scope_id,
        assignment_priority=assignment_priority,
        profile_priority=profile_priority,
        assignment_effective_from=assignment_effective_from,
        assignment_effective_to=assignment_effective_to,
        profile_effective_from=profile_effective_from,
        profile_effective_to=profile_effective_to,
        profile_version=profile_version,
        assignment_is_active=assignment_is_active,
        profile_is_active=profile_is_active,
    )


def test_customer_scope_beats_product_and_default() -> None:
    selected = select_pricing_profile(
        (
            candidate(
                "00000000-0000-0000-0000-000000000010",
                scope_type="DEFAULT",
            ),
            candidate(
                "00000000-0000-0000-0000-000000000020",
                scope_type="PRODUCT",
                scope_id=PRODUCT_ID,
            ),
            candidate(
                "00000000-0000-0000-0000-000000000030",
                scope_type="CUSTOMER",
                scope_id=CUSTOMER_ID,
            ),
        ),
        as_of=AS_OF,
    )

    assert selected.profile_id == UUID("00000000-0000-0000-0000-000000000030")
    assert selected.scope_type == "CUSTOMER"
    assert selected.scope_id == CUSTOMER_ID


def test_product_scope_beats_default() -> None:
    selected = select_pricing_profile(
        (
            candidate("00000000-0000-0000-0000-000000000010"),
            candidate(
                "00000000-0000-0000-0000-000000000020",
                scope_type="PRODUCT",
                scope_id=PRODUCT_ID,
            ),
        ),
        as_of=AS_OF,
    )

    assert selected.profile_id == UUID("00000000-0000-0000-0000-000000000020")


def test_higher_assignment_priority_wins_within_same_scope() -> None:
    selected = select_pricing_profile(
        (
            candidate(
                "00000000-0000-0000-0000-000000000010",
                scope_type="CUSTOMER",
                scope_id=CUSTOMER_ID,
                assignment_priority=10,
            ),
            candidate(
                "00000000-0000-0000-0000-000000000020",
                scope_type="CUSTOMER",
                scope_id=CUSTOMER_ID,
                assignment_priority=20,
            ),
        ),
        as_of=AS_OF,
    )

    assert selected.profile_id == UUID("00000000-0000-0000-0000-000000000020")


def test_higher_profile_priority_wins_after_assignment_priority() -> None:
    selected = select_pricing_profile(
        (
            candidate(
                "00000000-0000-0000-0000-000000000010",
                profile_priority=10,
            ),
            candidate(
                "00000000-0000-0000-0000-000000000020",
                profile_priority=20,
            ),
        ),
        as_of=AS_OF,
    )

    assert selected.profile_id == UUID("00000000-0000-0000-0000-000000000020")


def test_future_assignment_is_ignored() -> None:
    selected = select_pricing_profile(
        (
            candidate("00000000-0000-0000-0000-000000000010"),
            candidate(
                "00000000-0000-0000-0000-000000000020",
                assignment_effective_from=date(2026, 9, 12),
            ),
        ),
        as_of=AS_OF,
    )

    assert selected.profile_id == UUID("00000000-0000-0000-0000-000000000010")


def test_expired_assignment_is_ignored() -> None:
    selected = select_pricing_profile(
        (
            candidate("00000000-0000-0000-0000-000000000010"),
            candidate(
                "00000000-0000-0000-0000-000000000020",
                assignment_effective_to=date(2026, 9, 11),
            ),
        ),
        as_of=AS_OF,
    )

    assert selected.profile_id == UUID("00000000-0000-0000-0000-000000000010")


def test_inactive_assignment_is_ignored() -> None:
    selected = select_pricing_profile(
        (
            candidate("00000000-0000-0000-0000-000000000010"),
            candidate(
                "00000000-0000-0000-0000-000000000020",
                assignment_is_active=False,
            ),
        ),
        as_of=AS_OF,
    )

    assert selected.profile_id == UUID("00000000-0000-0000-0000-000000000010")


def test_inactive_profile_is_ignored() -> None:
    selected = select_pricing_profile(
        (
            candidate("00000000-0000-0000-0000-000000000010"),
            candidate(
                "00000000-0000-0000-0000-000000000020",
                profile_is_active=False,
            ),
        ),
        as_of=AS_OF,
    )

    assert selected.profile_id == UUID("00000000-0000-0000-0000-000000000010")


def test_newer_effective_profile_wins_when_other_precedence_is_equal() -> None:
    selected = select_pricing_profile(
        (
            candidate(
                "00000000-0000-0000-0000-000000000010",
                profile_effective_from=date(2026, 1, 1),
            ),
            candidate(
                "00000000-0000-0000-0000-000000000020",
                profile_effective_from=date(2026, 8, 1),
            ),
        ),
        as_of=AS_OF,
    )

    assert selected.profile_id == UUID("00000000-0000-0000-0000-000000000020")


def test_final_tie_break_is_deterministic_and_independent_of_input_order() -> None:
    first = candidate("00000000-0000-0000-0000-000000000010")
    second = candidate("00000000-0000-0000-0000-000000000020")

    forward = select_pricing_profile((first, second), as_of=AS_OF)
    reversed_order = select_pricing_profile((second, first), as_of=AS_OF)

    assert forward.profile_id == UUID("00000000-0000-0000-0000-000000000020")
    assert reversed_order == forward


def test_no_effective_profile_raises_clear_domain_error() -> None:
    with pytest.raises(PricingProfileSelectionError, match="No effective pricing profile"):
        select_pricing_profile(
            (
                candidate(
                    "00000000-0000-0000-0000-000000000010",
                    assignment_is_active=False,
                ),
            ),
            as_of=AS_OF,
        )
