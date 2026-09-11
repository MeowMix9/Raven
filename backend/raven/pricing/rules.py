from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import UUID


class PricingRuleEvaluationError(ValueError):
    """Raised when a configured pricing rule cannot be evaluated safely."""


@dataclass(frozen=True, slots=True)
class PricingRule:
    id: UUID
    name: str
    priority: int
    condition_group: dict[str, Any]
    action: dict[str, Any]
    is_enabled: bool = True


@dataclass(frozen=True, slots=True)
class RuleEvaluationResult:
    applied_rule_ids: tuple[UUID, ...]
    changes: tuple[dict[str, Any], ...]


class PricingRuleEvaluator:
    """Evaluate configured pricing rules without embedding pricing policy."""

    def evaluate(
        self,
        rules: tuple[PricingRule, ...],
        context: dict[str, Any],
    ) -> RuleEvaluationResult:
        applied: list[UUID] = []
        changes: list[dict[str, Any]] = []

        for rule in sorted(rules, key=lambda item: (-item.priority, str(item.id))):
            if not rule.is_enabled:
                continue
            if not _matches(rule.condition_group, context):
                continue

            change = _normalize_action(rule.action)
            applied.append(rule.id)
            changes.append(change)

        return RuleEvaluationResult(
            applied_rule_ids=tuple(applied),
            changes=tuple(changes),
        )


def _matches(condition: dict[str, Any], context: dict[str, Any]) -> bool:
    if not condition:
        return True
    if not isinstance(condition, dict):
        raise PricingRuleEvaluationError("Rule condition must be an object")

    if "all" in condition:
        items = condition["all"]
        if not isinstance(items, list):
            raise PricingRuleEvaluationError("'all' must be a list")
        return all(_matches(item, context) for item in items)

    if "any" in condition:
        items = condition["any"]
        if not isinstance(items, list):
            raise PricingRuleEvaluationError("'any' must be a list")
        return any(_matches(item, context) for item in items)

    field = condition.get("field")
    operator = condition.get("operator")
    expected = condition.get("value")
    if not isinstance(field, str) or not field:
        raise PricingRuleEvaluationError("Rule condition requires a field")
    if not isinstance(operator, str):
        raise PricingRuleEvaluationError("Rule condition requires an operator")

    actual = _get_context_value(context, field)
    return _compare(actual, operator, expected)


def _get_context_value(context: dict[str, Any], field: str) -> Any:
    value: Any = context
    for part in field.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def _compare(actual: Any, operator: str, expected: Any) -> bool:
    operator = operator.lower()

    if operator == "eq":
        return actual == expected
    if operator == "ne":
        return actual != expected
    if operator in {"gt", "gte", "lt", "lte"}:
        if actual is None:
            return False
        try:
            left, right = _comparable(actual, expected)
            return {
                "gt": left > right,
                "gte": left >= right,
                "lt": left < right,
                "lte": left <= right,
            }[operator]
        except TypeError as exc:
            raise PricingRuleEvaluationError(
                f"Values are not comparable for operator '{operator}'"
            ) from exc
    if operator == "in":
        if not isinstance(expected, (list, tuple, set, frozenset)):
            raise PricingRuleEvaluationError("'in' requires a collection value")
        return actual in expected
    if operator == "not_in":
        if not isinstance(expected, (list, tuple, set, frozenset)):
            raise PricingRuleEvaluationError("'not_in' requires a collection value")
        return actual not in expected
    if operator == "contains":
        try:
            return expected in actual
        except TypeError as exc:
            raise PricingRuleEvaluationError("'contains' requires a container") from exc
    if operator == "starts_with":
        return isinstance(actual, str) and isinstance(expected, str) and actual.startswith(expected)
    if operator == "ends_with":
        return isinstance(actual, str) and isinstance(expected, str) and actual.endswith(expected)
    if operator == "is_null":
        return actual is None
    if operator == "is_not_null":
        return actual is not None

    raise PricingRuleEvaluationError(f"Unsupported rule operator: {operator}")


def _comparable(actual: Any, expected: Any) -> tuple[Any, Any]:
    if isinstance(actual, Decimal) and isinstance(expected, (int, float, str)):
        return actual, Decimal(str(expected))
    if isinstance(expected, Decimal) and isinstance(actual, (int, float, str)):
        return Decimal(str(actual)), expected
    return actual, expected


def _normalize_action(action: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(action, dict) or not action:
        raise PricingRuleEvaluationError("Rule action must be a non-empty object")

    result = dict(action)
    if "type" not in result:
        raise PricingRuleEvaluationError("Rule action requires a type")
    if not isinstance(result["type"], str) or not result["type"]:
        raise PricingRuleEvaluationError("Rule action type must be a non-empty string")
    return result
