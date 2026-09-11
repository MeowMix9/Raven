"""Application service boundaries for quote operations.

Business rules will be implemented behind these services. API handlers and
future Horseman jobs should depend on these boundaries rather than reaching
into persistence models directly.
"""

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CalculateQuoteRequest:
    """Input required to calculate a quote.

    Pricing values are intentionally absent here. They are resolved from
    persisted configuration at calculation time.
    """

    customer_id: UUID
    items: tuple["QuoteItemRequest", ...]
    pricing_profile_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class QuoteItemRequest:
    product_id: UUID
    quantity: Decimal
    vendor_product_id: UUID | None = None
    options: dict[str, object] | None = None


@dataclass(frozen=True, slots=True)
class CalculateQuoteResult:
    subtotal: Decimal
    total_cost: Decimal
    total_price: Decimal
    gross_profit: Decimal
    gross_margin_percent: Decimal
    calculation_snapshot: dict[str, object]


class CalculateQuote:
    """Application boundary for deterministic quote calculation."""

    def __init__(self, pricing_resolver: object, calculator: object) -> None:
        self._pricing_resolver = pricing_resolver
        self._calculator = calculator

    def execute(self, request: CalculateQuoteRequest) -> CalculateQuoteResult:
        """Calculate a quote using configured pricing.

        The concrete resolver/calculator implementations are intentionally not
        supplied yet. This boundary lets the API and automation layers be
        built without coupling them to persistence or calculation details.
        """

        raise NotImplementedError("Quote calculation service is not implemented yet")
