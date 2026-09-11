from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID


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
    """Evaluates configured pricing rules without embedding pricing policy."""

    def evaluate(
        self,
        rules: tuple[PricingRule, ...],
        context: dict[str, Any],
    ) -> RuleEvaluationResult:
        raise NotImplementedError("Pricing rule evaluation is not wired yet")
