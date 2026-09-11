from datetime import date
from decimal import Decimal
from uuid import UUID

from raven.pricing.models import ResolvedPricingValue
from raven.pricing.pipeline import CalculationLine, CalculationResult, CalculationTraceEntry
from raven.pricing.resolver import ResolvedPricingContext
from raven.pricing.rules import RuleEvaluationResult
from raven.quotes.snapshot import CalculationSnapshot
from raven.infrastructure.quotes.repository import _snapshot_from_dict


PROFILE_ID = UUID("00000000-0000-0000-0000-000000000001")
RULE_ID = UUID("00000000-0000-0000-0000-000000000002")


def test_persisted_snapshot_round_trips_without_float_conversion() -> None:
    snapshot = CalculationSnapshot.from_calculation(
        pricing=ResolvedPricingContext(
            profile_id=PROFILE_ID,
            as_of=date(2026, 9, 11),
            values=(
                ResolvedPricingValue(
                    key="markup_percent",
                    value=Decimal("0.2500"),
                    source_profile_id=PROFILE_ID,
                ),
            ),
        ),
        rules=RuleEvaluationResult(
            applied_rule_ids=(RULE_ID,),
            changes=({
                "type": "apply_markup",
                "target": "total_price",
                "value_key": "markup_percent",
            },),
        ),
        calculation=CalculationResult(
            lines=(
                CalculationLine(
                    description="Test",
                    quantity=Decimal("10"),
                    unit_cost=Decimal("2.00"),
                    extended_cost=Decimal("20.00"),
                ),
            ),
            subtotal_cost=Decimal("20.00"),
            total_cost=Decimal("20.00"),
            total_price=Decimal("25.0000"),
            gross_profit=Decimal("5.0000"),
            gross_margin_percent=Decimal("20.0000"),
            applied_rule_ids=(RULE_ID,),
            trace=(
                CalculationTraceEntry(
                    rule_id=RULE_ID,
                    action_type="apply_markup",
                    target="total_price",
                    operand_source="pricing_value",
                    operand_key="markup_percent",
                    operand=Decimal("0.2500"),
                    before=Decimal("20.00"),
                    after=Decimal("25.0000"),
                ),
            ),
        ),
        engine_version="raven-pricing-v1",
        pricing_profile_version=4,
    )

    restored = _snapshot_from_dict(snapshot.to_dict())

    assert restored is not None
    assert restored.pricing_profile_id == PROFILE_ID
    assert restored.pricing_profile_version == 4
    assert restored.pricing_values[0].value == "0.2500"
    assert restored.calculation.total_price == Decimal("25.0000")
    assert restored.calculation.gross_margin_percent == Decimal("20.0000")
    assert restored.calculation.trace[0].operand == Decimal("0.2500")
