from datetime import date
from uuid import uuid4

from raven.quotes.models import Quote, QuoteItem
from raven.quotes.persistence import SaveQuote


class FakeQuoteRepository:
    def __init__(self) -> None:
        self.saved: Quote | None = None

    def save(self, quote: Quote) -> None:
        self.saved = quote

    def get_by_id(self, quote_id):
        return self.saved if self.saved and self.saved.quote_id == quote_id else None

    def get_by_number(self, quote_number):
        return self.saved if self.saved and self.saved.quote_number == quote_number else None


def test_save_quote_delegates_to_repository() -> None:
    repository = FakeQuoteRepository()
    quote = Quote.create(
        quote_number="Q-1001",
        customer_id=uuid4(),
        created_by_user_id=uuid4(),
        pricing_profile_id=uuid4(),
        quote_date=date(2026, 9, 11),
        expiration_date=None,
        currency="USD",
        items=(
            QuoteItem(
                line_number=1,
                product_id=uuid4(),
                description="Test product",
                quantity=1,
                unit_of_measure="EA",
                unit_cost=10,
                extended_cost=10,
            ),
        ),
    )

    result = SaveQuote(repository).execute(quote)

    assert repository.saved is quote
    assert result.quote_id == quote.quote_id
    assert result.quote_number == "Q-1001"
