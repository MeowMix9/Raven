from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PricingResolutionRequest:
    profile_id: UUID
    as_of: date
    customer_id: UUID | None = None
    product_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class ResolvedPricingValue:
    key: str
    value: Decimal | str | bool
    source_profile_id: UUID


@dataclass(frozen=True, slots=True)
class ResolvedPricingContext:
    profile_id: UUID
    as_of: date
    values: tuple[ResolvedPricingValue, ...]


class PricingResolver:
    """Application boundary for deterministic pricing-value resolution.

    Persistence and scope-selection rules will be supplied by repositories.
    The resolver itself must never contain business pricing constants.
    """

    def resolve(self, request: PricingResolutionRequest) -> ResolvedPricingContext:
        raise NotImplementedError("Pricing resolution repository is not wired yet")
