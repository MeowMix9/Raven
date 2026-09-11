from decimal import Decimal
from uuid import UUID

import pytest

from raven.pricing.rules import (
    PricingRule,
    PricingRuleEvaluationError,
    PricingRuleEvaluator,
)


def rule(rule_id: str, priority: int, condition: dict, action: dict, enabled: bool = True) -> PricingRule:
    return PricingRule(
        id=UUID(rule_id),
        name=f"Rule {priority}",
        priority=priority,
        condition_group=condition,
        action=action,
        is_enabled=enabled,
    )


def test_matching_rule_produces_configured_action() -> None:
    evaluator = PricingRuleEvaluator()
    pricing_rule = rule(
        "00000000-0000-0000-0000-000000000001",
        10,
        {"field": "quantity", "operator": "gte", "value": 100},
        {"type": "apply_markup", "value": "0.25"},
    )

    result = evaluator.evaluate((pricing_rule,), {"quantity": Decimal("125")})

    assert result.applied_rule_ids == (pricing_rule.id,)
    assert result.changes == ({"type": "apply_markup", "value": "0.25"},)


def test_non_matching_rule_is_ignored() -> None:
    evaluator = PricingRuleEvaluator()
    pricing_rule = rule(
        "00000000-0000-0000-0000-000000000002",
        10,
        {"field": "quantity", "operator": "gte", "value": 100},
        {"type": "apply_markup", "value": "0.25"},
    )

    result = evaluator.evaluate((pricing_rule,), {"quantity": 50})

    assert result.applied_rule_ids == ()
    assert result.changes == ()


def test_disabled_rule_is_ignored() -> None:
    evaluator = PricingRuleEvaluator()
    pricing_rule = rule(
        "00000000-0000-0000-0000-000000000003",
        10,
        {},
        {"type": "rush_fee", "value": "15"},
        enabled=False,
    )

    result = evaluator.evaluate((pricing_rule,), {})

    assert result.applied_rule_ids == ()


def test_all_conditions_must_match() -> None:
    evaluator = PricingRuleEvaluator()
    pricing_rule = rule(
        "00000000-0000-0000-0000-000000000004",
        10,
        {
            "all": [
                {"field": "quantity", "operator": "gte", "value": 100},
                {"field": "product.category", "operator": "eq", "value": "shirt"},
            ]
        },
        {"type": "discount", "value": "0.10"},
    )

    assert evaluator.evaluate((pricing_rule,), {"quantity": 100, "product": {"category": "shirt"}}).applied_rule_ids == (pricing_rule.id,)
    assert evaluator.evaluate((pricing_rule,), {"quantity": 100, "product": {"category": "hat"}}).applied_rule_ids == ()


def test_any_condition_can_match() -> None:
    evaluator = PricingRuleEvaluator()
    pricing_rule = rule(
        "00000000-0000-0000-0000-000000000005",
        10,
        {
            "any": [
                {"field": "customer.type", "operator": "eq", "value": "wholesale"},
                {"field": "quantity", "operator": "gte", "value": 500},
            ]
        },
        {"type": "minimum_charge", "value": "100"},
    )

    result = evaluator.evaluate((pricing_rule,), {"customer": {"type": "retail"}, "quantity": 500})

    assert result.applied_rule_ids == (pricing_rule.id,)


def test_rules_execute_in_priority_order() -> None:
    evaluator = PricingRuleEvaluator()
    low = rule(
        "00000000-0000-0000-0000-000000000010",
        10,
        {},
        {"type": "low"},
    )
    high = rule(
        "00000000-0000-0000-0000-000000000011",
        20,
        {},
        {"type": "high"},
    )

    result = evaluator.evaluate((low, high), {})

    assert result.applied_rule_ids == (high.id, low.id)


def test_supported_comparison_operators() -> None:
    evaluator = PricingRuleEvaluator()
    context = {"value": 10, "text": "Raven", "items": ["a", "b"]}

    for operator, expected in (("eq", 10), ("gte", 10), ("gt", 9), ("lte", 10), ("lt", 11)):
        pricing_rule = rule(
            "00000000-0000-0000-0000-000000000020",
            1,
            {"field": "value", "operator": operator, "value": expected},
            {"type": "test"},
        )
        assert evaluator.evaluate((pricing_rule,), context).applied_rule_ids == (pricing_rule.id,)

    for operator, expected in (("ne", 11), ("in", [9, 10, 11]), ("not_in", [1, 2]), ("contains", "a"), ("starts_with", "Ra"), ("ends_with", "en")):
        field = "text" if operator in {"starts_with", "ends_with"} else "items" if operator == "contains" else "value"
        pricing_rule = rule(
            "00000000-0000-0000-0000-000000000021",
            1,
            {"field": field, "operator": operator, "value": expected},
            {"type": "test"},
        )
        assert evaluator.evaluate((pricing_rule,), context).applied_rule_ids == (pricing_rule.id,)


def test_null_operators_work_for_missing_fields() -> None:
    evaluator = PricingRuleEvaluator()
    is_null = rule(
        "00000000-0000-0000-0000-000000000030",
        1,
        {"field": "missing", "operator": "is_null"},
        {"type": "test"},
    )
    is_not_null = rule(
        "00000000-0000-0000-0000-000000000031",
        1,
        {"field": "value", "operator": "is_not_null"},
        {"type": "test"},
    )

    result = evaluator.evaluate((is_null, is_not_null), {"value": 1})

    assert result.applied_rule_ids == (is_null.id, is_not_null.id)


def test_invalid_operator_raises() -> None:
    evaluator = PricingRuleEvaluator()
    pricing_rule = rule(
        "00000000-0000-0000-0000-000000000040",
        1,
        {"field": "value", "operator": "magic", "value": 1},
        {"type": "test"},
    )

    with pytest.raises(PricingRuleEvaluationError, match="Unsupported rule operator"):
        evaluator.evaluate((pricing_rule,), {"value": 1})


def test_invalid_action_raises() -> None:
    evaluator = PricingRuleEvaluator()
    pricing_rule = rule(
        "00000000-0000-0000-0000-000000000041",
        1,
        {},
        {},
    )

    with pytest.raises(PricingRuleEvaluationError, match="non-empty object"):
        evaluator.evaluate((pricing_rule,), {})
