from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID


class PricingProfileSelectionError(LookupError):
    """Raised when no active pricing profile can be selected."""


@dataclass(frozen=True, slots=True)
class PricingProfileCandidate:
    """A pricing profile assignment considered by the domain selector."""

    profile_id: UUID
    scope_type: str
    scope_id: UUID | None
    assignment_priority: int
    profile_priority: int
    assignment_effective_from: date | None
    assignment_effective_to: date | None
    profile_effective_from: date | None
    profile_effective_to: date | None
    profile_version: int
    assignment_is_active: bool = True
    profile_is_active: bool = True


@dataclass(frozen=True, slots=True)
class PricingProfileSelection:
    """The selected profile plus the assignment that caused it to win."""

    profile_id: UUID
    scope_type: str
    scope_id: UUID | None


# Scope specificity is an algorithmic precedence rule, not a pricing value.
_SCOPE_SPECIFICITY: dict[str, int] = {
    "CUSTOMER": 3,
    "PRODUCT": 2,
    "DEFAULT": 1,
    "GLOBAL": 1,
}


def _specificity(candidate: PricingProfileCandidate) -> int:
    return _SCOPE_SPECIFICITY.get(candidate.scope_type.upper(), 0)


def select_pricing_profile(
    candidates: tuple[PricingProfileCandidate, ...],
    *,
    as_of: date,
) -> PricingProfileSelection:
    """Select one effective pricing profile deterministically.

    Precedence, from strongest to weakest:

    1. Scope specificity: customer, product, then default/global.
    2. Assignment priority.
    3. Profile priority.
    4. Most recently effective profile.
    5. Highest profile version.
    6. Stable UUID ordering as the final deterministic tie-breaker.

    Pricing amounts and business-specific rates are never embedded here.
    """

    effective = tuple(
        candidate
        for candidate in candidates
        if _is_effective(candidate, as_of=as_of)
    )

    if not effective:
        raise PricingProfileSelectionError(
            f"No effective pricing profile is available for {as_of.isoformat()}"
        )

    selected = max(
        effective,
        key=lambda candidate: (
            _specificity(candidate),
            candidate.assignment_priority,
            candidate.profile_priority,
            _most_recent_effective_date(candidate),
            candidate.profile_version,
            candidate.profile_id.hex,
        ),
    )

    return PricingProfileSelection(
        profile_id=selected.profile_id,
        scope_type=selected.scope_type,
        scope_id=selected.scope_id,
    )


def _is_effective(candidate: PricingProfileCandidate, *, as_of: date) -> bool:
    if not candidate.assignment_is_active or not candidate.profile_is_active:
        return False

    if not _date_range_contains(
        as_of,
        candidate.assignment_effective_from,
        candidate.assignment_effective_to,
    ):
        return False

    return _date_range_contains(
        as_of,
        candidate.profile_effective_from,
        candidate.profile_effective_to,
    )


def _date_range_contains(
    value: date,
    effective_from: date | None,
    effective_to: date | None,
) -> bool:
    if effective_from is not None and effective_from > value:
        return False
    if effective_to is not None and effective_to <= value:
        return False
    return True


def _most_recent_effective_date(candidate: PricingProfileCandidate) -> date:
    """Return the strongest effective-start date available for tie-breaking."""

    return max(
        candidate.assignment_effective_from or date.min,
        candidate.profile_effective_from or date.min,
    )
