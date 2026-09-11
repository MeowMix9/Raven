from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from raven.quotes.calculation import CalculateQuote, QuoteCalculationRequest
from raven.quotes.models import Quote
from raven.quotes.persistence import SaveQuote, SaveQuoteResult


@dataclass(frozen=True, slots=True)
class QuoteServiceResult:
    quote: Quote
    saved: SaveQuoteResult


class QuoteService:
    def __init__(self, calculator: CalculateQuote, saver: SaveQuote) -> None:
        self._calculator = calculator
        self._saver = saver

    def calculate_and_save(
        self,
        quote: Quote,
        *,
        as_of: date | None = None,
        context: dict[str, object] | None = None,
        engine_version: str = "raven-pricing-v1",
        pricing_profile_version: int | None = None,
    ) -> QuoteServiceResult:
        result = self._calculator.execute(
            QuoteCalculationRequest(
                profile_id=quote.pricing_profile_id,
                as_of=as_of or quote.quote_date,
                lines=quote.calculation_lines(),
                customer_id=quote.customer_id,
                context=context,
                engine_version=engine_version,
                pricing_profile_version=pricing_profile_version,
            )
        )
        quote.mark_calculated(result.snapshot)
        saved = self._saver.execute(quote)
        return QuoteServiceResult(quote=quote, saved=saved)
