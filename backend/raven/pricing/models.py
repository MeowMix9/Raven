from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ResolvedPricingValue:
    key: str
    value: Decimal | str | bool
    source_profile_id: UUID
