from __future__ import annotations

from typing import Protocol
from uuid import UUID

from raven.quotes.models import Quote


class QuoteRepository(Protocol):
    """Persistence contract for the quote domain.

    The quote domain does not know whether quotes are stored in SQLAlchemy,
    another database, an API, or a test double.
    """

    def save(self, quote: Quote) -> None:
        ...

    def get_by_id(self, quote_id: UUID) -> Quote | None:
        ...

    def get_by_number(self, quote_number: str) -> Quote | None:
        ...
