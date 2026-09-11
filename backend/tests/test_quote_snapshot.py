from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest

from raven.pricing.models import ResolvedPricingValue
from raven.pricing.pipeline import (
    CalculationLine,
    CalculationResult,
    CalculationTraceEntry,
)
from raven.pricing.rules import RuleEvaluationResult
from raven.pricing.resolver import ResolvedPricingContext
from raven.quotes.snapshot import CalculationSnapshot


PROFILE_ID = UUID("00000000-0000-0000-0000-000000000001")
SOURCE_PROFILE_ID = UUID("00000000-0000-0000-0000-000000000002")
RULE_ID = UUID("00000000-0000-0000-0000-000000000003")


def _calculation() -> CalculationResult:
    return CalculationResult(
        lines=(
            CalculationLine(
                description="Test item",
                quantity=Decimal("10"),
                unit_cost=Decimal("20"),
                extended_cost=Decimal("200"),
            ),
        ),
        subtotal_cost=Decimal("200"),
        total_cost=Decimal("200"),
        total_price=Decimal("250"),
        gross_profit=Decimal("50"),
        gross_margin_percent=Decimal("20"),
        applied_rule_ids=(RULE_ID,),
        trace=(
            CalculationTraceEntry(
                rule_id=RULE_ID,
                action_type="apply_markup",
                target="total_price",
                operand_source="pricing_value",
                operand_key="markup_percent",
                operand=Decimal("0.25"),
                before=Decimal("200"),
                after=Decimal("250"),
            ),
        ),
    )


def test_snapshot_captures_resolved_pricing_and_rules() -> None:
    pricing = ResolvedPricingContext(
        profile_id=PROFILE_ID,
        as_of=date(2026, 9, 11),
        values=(
            ResolvedPricingValue(
                key="markup_percent",
                value=Decimal("0.25"),
                source_profile_id=SOURCE_PROFILE_ID,
            ),
        ),
    )
    rules = RuleEvaluationResult(
        applied_rule_ids=(RULE_ID,),
        changes=({
            "type": "apply_markup",
            "target": "total_price",
            "value_key": "markup_percent",
            "metadata": {"tier": "standard"},
        },),
    )

    snapshot = CalculationSnapshot.from_calculation(
        pricing=pricing,
        rules=rules,
        calculation=_calculation(),
        engine_version="raven-pricing-1",
        pricing_profile_version=7,
    )

    assert snapshot.pricing_profile_id == PROFILE_ID
    assert snapshot.pricing_profile_version == 7
    assert snapshot.pricing_values[0].value == Decimal("0.25")
    assert snapshot.applied_rule_ids == (RULE_ID,)
    assert snapshot.rule_changes[0].rule_id == RULE_ID
    assert snapshot.engine_version == "raven-pricing-1"


def test_snapshot_freezes_nested_rule_change_data() -> None:
    pricing = ResolvedPricingContext(
        profile_id=PROFILE_ID,
        as_of=date(2026, 9, 11),
        values=(),
    )
    metadata = {"tier": "standard"}
    change = {
        "type": "apply_markup",
        "target": "total_price",
        "metadata": metadata,
    }

    snapshot = CalculationSnapshot.from_calculation(
        pricing=pricing,
        rules=RuleEvaluationResult(
            applied_rule_ids=(RULE_ID,),
            changes=(change,),
        ),
        calculation=_calculation(),
        engine_version="raven-pricing-1",
    )

    metadata["tier"] = "vip"
    change["target"] = "total_cost"

    assert dict(snapshot.rule_changes[0].action)["target"] == "total_price"
    assert dict(snapshot.rule_changes[0].action)["metadata"] == (("tier", "standard"),)


def test_snapshot_serializes_decimal_values_without_float_conversion() -> None:
    pricing = ResolvedPricingContext(
        profile_id=PROFILE_ID,
        as_of=date(2026, 9, 11),
        values=(
            ResolvedPricingValue(
                key="markup_percent",
                value=Decimal("0.2500"),
                source_profile_id=SOURCE_PROFILE_ID,
            ),
        ),
    )

    snapshot = CalculationSnapshot.from_calculation(
        pricing=pricing,
        rules=RuleEvaluationResult(applied_rule_ids=(), changes=()),
        calculation=_calculation(),
        engine_version="raven-pricing-1",
    )

    payload = snapshot.to_dict()

    assert payload["as_of"] == "2026-09-11"
    assert payload["pricing_values"][0]["value"] == "0.2500"
    assert payload["calculation"]["total_price"] == "250"
    assert payload["calculation"]["gross_margin_percent"] == "20"


def test_snapshot_rejects_mismatched_rule_ids_and_changes() -> None:
    pricing = ResolvedPricingContext(
        profile_id=PROFILE_ID,
        as_of=date(2026, 9, 11),
        values=(),
    )

    with pytest.raises(ValueError, match="matching lengths"):
        CalculationSnapshot.from_calculation(
            pricing=pricing,
            rules=RuleEvaluationResult(
                applied_rule_ids=(RULE_ID,),
                changes=(),
            ),
            calculation=_calculation(),
            engine_version="raven-pricing-1",
        )


def test_snapshot_rejects_blank_engine_version() -> None:
    pricing = ResolvedPricingContext(
        profile_id=PROFILE_ID,
        as_of=date(2026, 9, 11),
        values=(),
    )

    with pytest.raises(ValueError, match="engine version cannot be blank"):
        CalculationSnapshot.from_calculation(
            pricing=pricing,
            rules=RuleEvaluationResult(applied_rule_ids=(), changes=()),
            calculation=_calculation(),
            engine_version="   ",
        )
