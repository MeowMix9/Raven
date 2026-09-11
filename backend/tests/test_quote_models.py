from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from raven.pricing.models import ResolvedPricingValue
from raven.pricing.pipeline import CalculationLine, CalculationResult
from raven.pricing.resolver import ResolvedPricingContext
from raven.pricing.rules import RuleEvaluationResult
from raven.quotes.models import Quote, QuoteItem, QuoteStatus
from raven.quotes.snapshot import CalculationSnapshot


def item() -> QuoteItem:
    return QuoteItem(
        line_number=1,
        product_id=uuid4(),
        description="Test product",
        quantity=Decimal("10"),
        unit_of_measure="EA",
        unit_cost=Decimal("2.00"),
        extended_cost=Decimal("20.00"),
    )


def make_quote() -> Quote:
    return Quote.create(
        quote_number="Q-1001",
        customer_id=uuid4(),
        created_by_user_id=uuid4(),
        pricing_profile_id=uuid4(),
        quote_date=date(2026, 9, 11),
        expiration_date=date(2026, 10, 11),
        currency="usd",
        items=(item(),),
    )


def test_quote_creation_normalizes_identity_fields() -> None:
    quote = make_quote()

    assert quote.quote_number == "Q-1001"
    assert quote.currency == "USD"
    assert quote.status == QuoteStatus.DRAFT


def test_quote_requires_items() -> None:
    with pytest.raises(ValueError, match="at least one item"):
        Quote.create(
            quote_number="Q-1001",
            customer_id=uuid4(),
            created_by_user_id=uuid4(),
            pricing_profile_id=uuid4(),
            quote_date=date(2026, 9, 11),
            expiration_date=None,
            currency="USD",
            items=(),
        )


def test_quote_rejects_expiration_before_quote_date() -> None:
    with pytest.raises(ValueError, match="expiration date"):
        Quote.create(
            quote_number="Q-1001",
            customer_id=uuid4(),
            created_by_user_id=uuid4(),
            pricing_profile_id=uuid4(),
            quote_date=date(2026, 9, 11),
            expiration_date=date(2026, 9, 10),
            currency="USD",
            items=(item(),),
        )


def test_quote_calculation_lines_are_derived_from_items() -> None:
    quote = make_quote()
    lines = quote.calculation_lines()

    assert lines == (
        CalculationLine(
            description="Test product",
            quantity=Decimal("10"),
            unit_cost=Decimal("2.00"),
            extended_cost=Decimal("20.00"),
        ),
    )


def test_mark_calculated_uses_snapshot_as_historical_authority() -> None:
    quote = make_quote()
    calculation = CalculationResult(
        lines=quote.calculation_lines(),
        subtotal_cost=Decimal("20.00"),
        total_cost=Decimal("20.00"),
        total_price=Decimal("25.00"),
        gross_profit=Decimal("5.00"),
        gross_margin_percent=Decimal("20.00"),
        applied_rule_ids=(),
        trace=(),
    )
    pricing = ResolvedPricingContext(
        profile_id=quote.pricing_profile_id,
        as_of=quote.quote_date,
        values=(
            ResolvedPricingValue(
                key="markup_percent",
                value=Decimal("0.25"),
                source_profile_id=quote.pricing_profile_id,
            ),
        ),
    )
    snapshot = CalculationSnapshot.from_calculation(
        pricing=pricing,
        rules=RuleEvaluationResult(applied_rule_ids=(), changes=()),
        calculation=calculation,
        engine_version="raven-pricing-v1",
    )

    quote.mark_calculated(snapshot)

    assert quote.status == QuoteStatus.CALCULATED
    assert quote.calculation is calculation
    assert quote.calculation_snapshot is snapshot
    assert quote.calculation_engine_version == "raven-pricing-v1"


def test_mark_calculated_rejects_wrong_pricing_profile() -> None:
    quote = make_quote()
    snapshot = CalculationSnapshot.from_calculation(
        pricing=ResolvedPricingContext(
            profile_id=uuid4(),
            as_of=quote.quote_date,
            values=(),
        ),
        rules=RuleEvaluationResult(applied_rule_ids=(), changes=()),
        calculation=CalculationResult(
            lines=quote.calculation_lines(),
            subtotal_cost=Decimal("20"),
            total_cost=Decimal("20"),
            total_price=Decimal("20"),
            gross_profit=Decimal("0"),
            gross_margin_percent=Decimal("0"),
            applied_rule_ids=(),
            trace=(),
        ),
        engine_version="raven-pricing-v1",
    )

    with pytest.raises(ValueError, match="pricing profile"):
        quote.mark_calculated(snapshot)
