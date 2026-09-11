from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from raven.pricing.resolver import ResolvedPricingValue
from raven.pricing.rules import PricingRule


class PricingRepository(Protocol):
    """Persistence contract used by the pricing domain.

    Implementations may use SQLAlchemy, an API, or another durable store.
    The pricing engine does not depend on a particular persistence technology.
    """

    def resolve_profile_id(
        self,
        *,
        requested_profile_id: UUID,
        customer_id: UUID | None,
        product_id: UUID | None,
        as_of: date,
    ) -> UUID:
        ...

    def get_values(
        self,
        *,
        profile_id: UUID,
        as_of: date,
        quantity: Decimal | None = None,
    ) -> tuple[ResolvedPricingValue, ...]:
        ...

    def get_rules(
        self,
        *,
        profile_id: UUID,
        as_of: date,
    ) -> tuple[PricingRule, ...]:
        ...
