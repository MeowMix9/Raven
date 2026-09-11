from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from raven.pricing.models import ResolvedPricingValue
from raven.pricing.repositories import PricingRepository


@dataclass(frozen=True, slots=True)
class PricingResolutionRequest:
    profile_id: UUID
    as_of: date
    customer_id: UUID | None = None
    product_id: UUID | None = None
    quantity: Decimal | None = None


@dataclass(frozen=True, slots=True)
class ResolvedPricingContext:
    profile_id: UUID
    as_of: date
    values: tuple[ResolvedPricingValue, ...]

    def get(self, key: str) -> ResolvedPricingValue | None:
        for value in self.values:
            if value.key == key:
                return value
        return None


class PricingResolver:
    """Resolve the effective pricing configuration for a quote calculation."""

    def __init__(self, repository: PricingRepository) -> None:
        self._repository = repository

    def resolve(self, request: PricingResolutionRequest) -> ResolvedPricingContext:
        profile_id = self._repository.resolve_profile_id(
            requested_profile_id=request.profile_id,
            customer_id=request.customer_id,
            product_id=request.product_id,
            as_of=request.as_of,
        )
        values = self._repository.get_values(
            profile_id=profile_id,
            as_of=request.as_of,
            quantity=request.quantity,
        )
        return ResolvedPricingContext(
            profile_id=profile_id,
            as_of=request.as_of,
            values=values,
        )
