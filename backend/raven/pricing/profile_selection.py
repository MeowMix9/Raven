from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID


class PricingProfileSelectionError(LookupError):
    """Raised when no active pricing profile can be selected."""


@dataclass(frozen=True, slots=True)
class PricingProfileCandidate:
    """A pricing profile assignment eligible for deterministic selection.

    The persistence layer is responsible for loading candidate assignments and
    profile metadata. This selector intentionally contains no pricing values.
    """

    profile_id: UUID
    scope_type: str
    scope_id: UUID | None
    assignment_priority: int
    profile_priority: int
    effective_from: date | None
    profile_version: int


@dataclass(frozen=True, slots=True)
class PricingProfileSelection:
    """The selected profile plus the assignment that caused it to win."""

    profile_id: UUID
    scope_type: str
    scope_id: UUID | None


# Scope specificity is an algorithmic precedence rule, not a pricing value.
# Unknown scopes are deliberately lowest specificity so adding a new scope
# cannot silently outrank an explicitly supported scope.
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

    Candidates should already represent active assignments and active profiles.
    The selector still filters effective dates so the domain rule cannot be
    bypassed accidentally by a repository implementation.
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
            candidate.effective_from or date.min,
            candidate.profile_version,
            # max() chooses the greatest value. UUID hex gives us a stable,
            # database-independent final ordering without relying on row order.
            candidate.profile_id.hex,
        ),
    )

    return PricingProfileSelection(
        profile_id=selected.profile_id,
        scope_type=selected.scope_type,
        scope_id=selected.scope_id,
    )


def _is_effective(candidate: PricingProfileCandidate, *, as_of: date) -> bool:
    if candidate.effective_from is not None and candidate.effective_from > as_of:
        return False
    # Assignment/profile end dates are represented by the candidate's effective
    # start only at this layer. Repository adapters must exclude expired profile
    # and assignment records before constructing candidates.
    return True
