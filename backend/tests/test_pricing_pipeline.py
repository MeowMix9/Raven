from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from raven.pricing.models import ResolvedPricingValue
from raven.pricing.pipeline import (
    CalculationLine,
    PricingCalculationError,
    PricingCalculationPipeline,
)
from raven.pricing.resolver import ResolvedPricingContext
from raven.pricing.rules import RuleEvaluationResult


PROFILE_ID = UUID("00000000-0000-0000-0000-000000000001")


def pricing_context(*values: tuple[str, Decimal | str | bool]) -> ResolvedPricingContext:
    return ResolvedPricingContext(
        profile_id=PROFILE_ID,
        as_of=__import__("datetime").date(2026, 1, 1),
        values=tuple(
            ResolvedPricingValue(key=key, value=value, source_profile_id=PROFILE_ID)
            for key, value in values
        ),
    )


def lines() -> tuple[CalculationLine, ...]:
    return (
        CalculationLine(
            description="Test product",
            quantity=Decimal("100"),
            unit_cost=Decimal("2.00"),
            extended_cost=Decimal("200.00"),
        ),
    )


def result_for(actions: tuple[dict, ...], pricing: ResolvedPricingContext | None = None):
    rules = RuleEvaluationResult(
        applied_rule_ids=tuple(uuid4() for _ in actions),
        changes=actions,
    )
    return PricingCalculationPipeline().calculate(
        pricing or pricing_context(),
        rules,
        lines(),
    )


def test_markup_resolves_operand_from_pricing_configuration() -> None:
    result = result_for(
        ({"type": "apply_markup", "target": "total_price", "value_key": "markup_percent"},),
        pricing_context(("markup_percent", Decimal("0.25"))),
    )

    assert result.total_cost == Decimal("200.00")
    assert result.total_price == Decimal("250.0000")
    assert result.gross_profit == Decimal("50.0000")
    assert result.gross_margin_percent == Decimal("20.00")
    assert result.trace[0].operand_source == "pricing_value"
    assert result.trace[0].operand_key == "markup_percent"


def test_actions_apply_in_rule_order() -> None:
    result = result_for(
        (
            {"type": "apply_markup", "target": "total_price", "value": "0.25"},
            {"type": "apply_discount", "target": "total_price", "value": "0.10"},
        )
    )

    assert result.total_price == Decimal("225.0000")
    assert [entry.action_type for entry in result.trace] == ["apply_markup", "apply_discount"]


def test_add_charge_is_applied_to_price() -> None:
    result = result_for(
        ({"type": "add_charge", "target": "total_price", "value": "15.00", "label": "Rush"},)
    )

    assert result.total_price == Decimal("215.00")
    assert result.trace[0].label == "Rush"


def test_set_minimum_raises_price_to_configured_minimum() -> None:
    result = result_for(
        ({"type": "set_minimum", "target": "total_price", "value_key": "minimum_charge"},),
        pricing_context(("minimum_charge", Decimal("300.00"))),
    )

    assert result.total_price == Decimal("300.00")
    assert result.gross_profit == Decimal("100.00")


def test_set_minimum_does_not_lower_existing_price() -> None:
    result = result_for(
        (
            {"type": "apply_markup", "target": "total_price", "value": "0.50"},
            {"type": "set_minimum", "target": "total_price", "value": "250.00"},
        )
    )

    assert result.total_price == Decimal("300.00")


def test_target_aliases_are_supported() -> None:
    result = result_for(
        ({"type": "apply_markup", "target": "price", "value": "0.10"},)
    )

    assert result.total_price == Decimal("220.00")
    assert result.trace[0].target == "total_price"


def test_missing_pricing_value_is_an_error() -> None:
    with pytest.raises(PricingCalculationError, match="was not resolved"):
        result_for(
            ({"type": "apply_markup", "target": "total_price", "value_key": "missing"},)
        )


def test_non_numeric_pricing_value_is_an_error() -> None:
    with pytest.raises(PricingCalculationError, match="must resolve to a numeric value"):
        result_for(
            ({"type": "apply_markup", "target": "total_price", "value_key": "markup"},),
            pricing_context(("markup", "twenty-five-percent")),
        )


def test_invalid_extended_cost_is_rejected() -> None:
    invalid_lines = (
        CalculationLine(
            description="Broken line",
            quantity=Decimal("10"),
            unit_cost=Decimal("2.00"),
            extended_cost=Decimal("19.00"),
        ),
    )
    rules = RuleEvaluationResult(applied_rule_ids=(), changes=())

    with pytest.raises(PricingCalculationError, match="Extended cost"):
        PricingCalculationPipeline().calculate(pricing_context(), rules, invalid_lines)


def test_zero_price_has_zero_margin_instead_of_dividing_by_zero() -> None:
    result = result_for(
        ({"type": "set_value", "target": "total_price", "value": "0"},)
    )

    assert result.total_price == Decimal("0")
    assert result.gross_profit == Decimal("-200.00")
    assert result.gross_margin_percent == Decimal("0")


def test_trace_records_before_and_after_values() -> None:
    rule_id = uuid4()
    rules = RuleEvaluationResult(
        applied_rule_ids=(rule_id,),
        changes=({"type": "add_amount", "target": "total_price", "value": "12.50"},),
    )

    result = PricingCalculationPipeline().calculate(pricing_context(), rules, lines())

    assert result.trace[0].rule_id == rule_id
    assert result.trace[0].before == Decimal("200.00")
    assert result.trace[0].after == Decimal("212.50")
