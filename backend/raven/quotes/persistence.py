from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from raven.quotes.models import Quote
from raven.quotes.repositories import QuoteRepository


@dataclass(frozen=True, slots=True)
class SaveQuoteResult:
    quote_id: UUID
    quote_number: str


class SaveQuote:
    """Application boundary for durable quote persistence."""

    def __init__(self, repository: QuoteRepository) -> None:
        self._repository = repository

    def execute(self, quote: Quote) -> SaveQuoteResult:
        self._repository.save(quote)
        return SaveQuoteResult(
            quote_id=quote.quote_id,
            quote_number=quote.quote_number,
        )
