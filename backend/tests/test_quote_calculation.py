from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from raven.pricing.models import ResolvedPricingValue
from raven.pricing.pipeline import CalculationLine
from raven.pricing.resolver import PricingResolver
from raven.pricing.rules import PricingRule
from raven.quotes.calculation import CalculateQuote, QuoteCalculationRequest


PROFILE_ID = UUID("00000000-0000-0000-0000-000000000001")


class FakePricingRepository:
    def __init__(self) -> None:
        self.rules = (
            PricingRule(
                id=uuid4(),
                name="Configured markup",
                priority=10,
                condition_group={"field": "quote.quantity", "operator": "gte", "value": 100},
                action={
                    "type": "apply_markup",
                    "target": "total_price",
                    "value_key": "markup_percent",
                },
            ),
        )
        self.requested_profile_id = None
        self.requested_customer_id = None
        self.requested_product_id = None

    def resolve_profile_id(self, *, requested_profile_id, customer_id, product_id, as_of):
        self.requested_profile_id = requested_profile_id
        self.requested_customer_id = customer_id
        self.requested_product_id = product_id
        return PROFILE_ID

    def get_values(self, *, profile_id, as_of, quantity=None):
        return (
            ResolvedPricingValue(
                key="markup_percent",
                value=Decimal("0.25"),
                source_profile_id=profile_id,
            ),
        )

    def get_rules(self, *, profile_id, as_of):
        assert profile_id == PROFILE_ID
        return self.rules


def make_service(repository: FakePricingRepository) -> CalculateQuote:
    return CalculateQuote(PricingResolver(repository), repository)


def test_calculate_quote_orchestrates_resolution_rules_pipeline_and_snapshot() -> None:
    repository = FakePricingRepository()
    customer_id = uuid4()
    product_id = uuid4()

    result = make_service(repository).execute(
        QuoteCalculationRequest(
            profile_id=UUID("00000000-0000-0000-0000-000000000099"),
            as_of=date(2026, 9, 11),
            customer_id=customer_id,
            product_id=product_id,
            quantity=Decimal("100"),
            lines=(
                CalculationLine(
                    description="Test product",
                    quantity=Decimal("100"),
                    unit_cost=Decimal("2.00"),
                    extended_cost=Decimal("200.00"),
                ),
            ),
        )
    )

    assert result.pricing_profile_id == PROFILE_ID
    assert result.calculation.total_cost == Decimal("200.00")
    assert result.calculation.total_price == Decimal("250.0000")
    assert result.calculation.applied_rule_ids == (repository.rules[0].id,)
    assert result.snapshot.pricing_profile_id == PROFILE_ID
    assert result.snapshot.calculation.total_price == Decimal("250.0000")
    assert repository.requested_customer_id == customer_id
    assert repository.requested_product_id == product_id


def test_calculate_quote_preserves_custom_context_for_rule_evaluation() -> None:
    repository = FakePricingRepository()
    repository.rules = (
        PricingRule(
            id=uuid4(),
            name="VIP markup",
            priority=10,
            condition_group={"field": "customer.tier", "operator": "eq", "value": "VIP"},
            action={"type": "add_amount", "target": "total_price", "value": "10"},
        ),
    )

    result = make_service(repository).execute(
        QuoteCalculationRequest(
            profile_id=PROFILE_ID,
            as_of=date(2026, 9, 11),
            lines=(
                CalculationLine(
                    description="Test product",
                    quantity=Decimal("1"),
                    unit_cost=Decimal("20.00"),
                    extended_cost=Decimal("20.00"),
                ),
            ),
            context={"customer": {"tier": "VIP"}},
        )
    )

    assert result.calculation.total_price == Decimal("30.00")
    assert result.snapshot.rule_changes[0].rule_id == repository.rules[0].id


def test_calculate_quote_rejects_non_object_quote_context() -> None:
    repository = FakePricingRepository()

    try:
        make_service(repository).execute(
            QuoteCalculationRequest(
                profile_id=PROFILE_ID,
                as_of=date(2026, 9, 11),
                lines=(),
                context={"quote": "invalid"},
            )
        )
    except ValueError as exc:
        assert "quote" in str(exc)
    else:
        raise AssertionError("Expected invalid quote context to raise ValueError")
