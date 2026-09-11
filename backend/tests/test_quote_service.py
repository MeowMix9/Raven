from datetime import date
from decimal import Decimal
from uuid import uuid4

from raven.pricing.models import ResolvedPricingValue
from raven.pricing.rules import PricingRule
from raven.quotes.calculation import CalculateQuote
from raven.quotes.models import Quote, QuoteItem
from raven.quotes.persistence import SaveQuote
from raven.quotes.service import QuoteService


class FakePricingRepository:
    def __init__(self, profile_id):
        self.profile_id = profile_id

    def resolve_profile_id(self, **kwargs):
        return self.profile_id

    def get_values(self, **kwargs):
        return (
            ResolvedPricingValue(
                key="markup_percent",
                value=Decimal("0.25"),
                source_profile_id=self.profile_id,
            ),
        )

    def get_rules(self, **kwargs):
        return (
            PricingRule(
                id=uuid4(),
                name="Configured markup",
                priority=100,
                condition_group={"all": []},
                action={
                    "type": "apply_markup",
                    "target": "total_price",
                    "value_key": "markup_percent",
                },
                is_enabled=True,
            ),
        )


class FakeQuoteRepository:
    def __init__(self):
        self.saved = None

    def save(self, quote):
        self.saved = quote

    def get_by_id(self, quote_id):
        return self.saved

    def get_by_number(self, quote_number):
        return self.saved


def test_quote_service_calculates_then_saves_snapshot():
    profile_id = uuid4()
    repository = FakePricingRepository(profile_id)
    quote_repository = FakeQuoteRepository()
    quote = Quote.create(
        quote_number="Q-2001",
        customer_id=uuid4(),
        created_by_user_id=uuid4(),
        pricing_profile_id=profile_id,
        quote_date=date(2026, 9, 11),
        expiration_date=None,
        currency="USD",
        items=(
            QuoteItem(
                line_number=1,
                product_id=uuid4(),
                description="Test product",
                quantity=Decimal("10"),
                unit_of_measure="EA",
                unit_cost=Decimal("20"),
                extended_cost=Decimal("200"),
                unit_price=Decimal("25"),
                extended_price=Decimal("250"),
            ),
        ),
    )

    result = QuoteService(
        CalculateQuote(
            pricing_resolver=__import__("raven.pricing.resolver", fromlist=["PricingResolver"]).PricingResolver(repository),
            pricing_repository=repository,
        ),
        SaveQuote(quote_repository),
    ).calculate_and_save(quote)

    assert result.quote.status.value == "calculated"
    assert result.quote.calculation_snapshot is not None
    assert result.quote.calculation.total_price == Decimal("250")
    assert quote_repository.saved is quote
