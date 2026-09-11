from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from raven.pricing.rules import RuleEvaluationResult
from raven.pricing.resolver import ResolvedPricingContext


@dataclass(frozen=True, slots=True)
class CalculationLine:
    description: str
    quantity: Decimal
    unit_cost: Decimal
    extended_cost: Decimal


@dataclass(frozen=True, slots=True)
class CalculationResult:
    lines: tuple[CalculationLine, ...]
    subtotal_cost: Decimal
    total_cost: Decimal
    applied_rule_ids: tuple[UUID, ...]


class PricingCalculationPipeline:
    """Pure calculation boundary fed entirely by resolved configuration."""

    def calculate(
        self,
        pricing: ResolvedPricingContext,
        rules: RuleEvaluationResult,
        lines: tuple[CalculationLine, ...],
    ) -> CalculationResult:
        subtotal = sum((line.extended_cost for line in lines), Decimal("0"))
        return CalculationResult(
            lines=lines,
            subtotal_cost=subtotal,
            total_cost=subtotal,
            applied_rule_ids=rules.applied_rule_ids,
        )
