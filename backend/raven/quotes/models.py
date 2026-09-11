from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from raven.pricing.pipeline import CalculationLine, CalculationResult


class QuoteStatus(StrEnum):
    DRAFT = "draft"
    CALCULATED = "calculated"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    SENT = "sent"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass(frozen=True, slots=True)
class QuoteItem:
    line_number: int
    product_id: UUID | None
    description: str
    quantity: Decimal
    unit_of_measure: str
    unit_cost: Decimal
    extended_cost: Decimal
    vendor_id: UUID | None = None
    vendor_product_id: UUID | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class Quote:
    """Domain representation of a quote independent of persistence or UI."""

    quote_id: UUID
    quote_number: str
    customer_id: UUID
    created_by_user_id: UUID
    pricing_profile_id: UUID
    quote_date: date
    expiration_date: date | None
    currency: str
    items: tuple[QuoteItem, ...]
    status: QuoteStatus = QuoteStatus.DRAFT
    notes: str | None = None
    calculation: CalculationResult | None = None
    calculation_engine_version: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def create(
        cls,
        *,
        quote_number: str,
        customer_id: UUID,
        created_by_user_id: UUID,
        pricing_profile_id: UUID,
        quote_date: date,
        expiration_date: date | None,
        currency: str,
        items: tuple[QuoteItem, ...],
        notes: str | None = None,
    ) -> "Quote":
        if not quote_number.strip():
            raise ValueError("Quote number cannot be blank")
        if not currency.strip():
            raise ValueError("Quote currency cannot be blank")
        if not items:
            raise ValueError("Quote must contain at least one item")
        if expiration_date is not None and expiration_date < quote_date:
            raise ValueError("Quote expiration date cannot precede quote date")

        return cls(
            quote_id=uuid4(),
            quote_number=quote_number.strip(),
            customer_id=customer_id,
            created_by_user_id=created_by_user_id,
            pricing_profile_id=pricing_profile_id,
            quote_date=quote_date,
            expiration_date=expiration_date,
            currency=currency.strip().upper(),
            items=items,
            notes=notes,
        )

    def mark_calculated(self, calculation: CalculationResult, *, engine_version: str) -> None:
        self.calculation = calculation
        self.calculation_engine_version = engine_version
        self.status = QuoteStatus.CALCULATED

    def calculation_lines(self) -> tuple[CalculationLine, ...]:
        return tuple(
            CalculationLine(
                description=item.description,
                quantity=item.quantity,
                unit_cost=item.unit_cost,
                extended_cost=item.extended_cost,
            )
            for item in self.items
        )
