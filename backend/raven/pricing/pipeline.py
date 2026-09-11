from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import UUID

from raven.pricing.actions import PricingAction, PricingActionValidationError, normalize_pricing_action
from raven.pricing.models import ResolvedPricingValue
from raven.pricing.rules import RuleEvaluationResult
from raven.pricing.resolver import ResolvedPricingContext


ZERO = Decimal("0")
HUNDRED = Decimal("100")


@dataclass(frozen=True, slots=True)
class CalculationLine:
    description: str
    quantity: Decimal
    unit_cost: Decimal
    extended_cost: Decimal


@dataclass(frozen=True, slots=True)
class CalculationTraceEntry:
    rule_id: UUID
    action_type: str
    target: str
    operand_source: str
    operand_key: str | None
    operand: Decimal
    before: Decimal
    after: Decimal
    label: str | None = None


@dataclass(frozen=True, slots=True)
class CalculationResult:
    lines: tuple[CalculationLine, ...]
    subtotal_cost: Decimal
    total_cost: Decimal
    total_price: Decimal
    gross_profit: Decimal
    gross_margin_percent: Decimal
    applied_rule_ids: tuple[UUID, ...]
    trace: tuple[CalculationTraceEntry, ...]


class PricingCalculationError(ValueError):
    """Raised when a pricing action cannot be safely calculated."""


class PricingCalculationPipeline:
    """Apply resolved, configured pricing actions deterministically.

    The pipeline contains calculation mechanics only. Business pricing values
    must arrive through resolved configuration or an explicitly configured
    action literal; no business rates or fees are embedded here.
    """

    def calculate(
        self,
        pricing: ResolvedPricingContext,
        rules: RuleEvaluationResult,
        lines: tuple[CalculationLine, ...],
    ) -> CalculationResult:
        self._validate_lines(lines)

        subtotal = sum((line.extended_cost for line in lines), ZERO)
        values: dict[str, Decimal] = {
            "subtotal_cost": subtotal,
            "total_cost": subtotal,
            "total_price": subtotal,
        }
        trace: list[CalculationTraceEntry] = []

        for rule_id, raw_action in zip(rules.applied_rule_ids, rules.changes, strict=True):
            action = self._normalize_action(raw_action)
            operand, source = self._resolve_operand(action, pricing)
            target = action.target
            if target is None:
                raise PricingCalculationError(
                    f"Pricing action '{action.type}' has no calculation target"
                )

            normalized_target = _normalize_target(target)
            if normalized_target not in values:
                raise PricingCalculationError(
                    f"Unsupported calculation target: {target}"
                )

            before = values[normalized_target]
            after = self._apply_action(action, before, operand)
            values[normalized_target] = after
            trace.append(
                CalculationTraceEntry(
                    rule_id=rule_id,
                    action_type=action.type,
                    target=normalized_target,
                    operand_source=source,
                    operand_key=action.value_key,
                    operand=operand,
                    before=before,
                    after=after,
                    label=action.label,
                )
            )

        total_cost = values["total_cost"]
        total_price = values["total_price"]
        gross_profit = total_price - total_cost
        gross_margin_percent = (
            (gross_profit / total_price) * HUNDRED if total_price != ZERO else ZERO
        )

        return CalculationResult(
            lines=lines,
            subtotal_cost=subtotal,
            total_cost=total_cost,
            total_price=total_price,
            gross_profit=gross_profit,
            gross_margin_percent=gross_margin_percent,
            applied_rule_ids=rules.applied_rule_ids,
            trace=tuple(trace),
        )

    @staticmethod
    def _normalize_action(raw_action: dict[str, Any]) -> PricingAction:
        try:
            return normalize_pricing_action(raw_action)
        except PricingActionValidationError as exc:
            raise PricingCalculationError(str(exc)) from exc

    @staticmethod
    def _resolve_operand(
        action: PricingAction,
        pricing: ResolvedPricingContext,
    ) -> tuple[Decimal, str]:
        if action.value_key is not None:
            resolved: ResolvedPricingValue | None = pricing.get(action.value_key)
            if resolved is None:
                raise PricingCalculationError(
                    f"Pricing value '{action.value_key}' was not resolved"
                )
            if not isinstance(resolved.value, Decimal):
                raise PricingCalculationError(
                    f"Pricing value '{action.value_key}' must resolve to a numeric value"
                )
            return resolved.value, "pricing_value"

        if isinstance(action.value, bool) or not isinstance(action.value, Decimal):
            raise PricingCalculationError(
                f"Pricing action '{action.type}' requires a numeric operand"
            )
        return action.value, "literal"

    @staticmethod
    def _apply_action(action: PricingAction, before: Decimal, operand: Decimal) -> Decimal:
        if action.type == "set_value":
            return operand
        if action.type in {"add_amount", "add_charge"}:
            return before + operand
        if action.type == "subtract_amount":
            return before - operand
        if action.type == "multiply":
            return before * operand
        if action.type in {"add_percent", "apply_markup"}:
            return before + (before * operand)
        if action.type in {"subtract_percent", "apply_discount"}:
            return before - (before * operand)
        if action.type == "set_minimum":
            return max(before, operand)
        raise PricingCalculationError(f"Unsupported pricing action type: {action.type}")

    @staticmethod
    def _validate_lines(lines: tuple[CalculationLine, ...]) -> None:
        for line in lines:
            if line.quantity < ZERO:
                raise PricingCalculationError("Line quantity cannot be negative")
            if line.unit_cost < ZERO:
                raise PricingCalculationError("Line unit cost cannot be negative")
            if line.extended_cost != line.quantity * line.unit_cost:
                raise PricingCalculationError(
                    f"Extended cost does not match quantity × unit cost for '{line.description}'"
                )


def _normalize_target(target: str) -> str:
    normalized = target.strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "cost": "total_cost",
        "price": "total_price",
        "sell_price": "total_price",
        "selling_price": "total_price",
        "minimum": "total_price",
        "subtotal": "subtotal_cost",
    }
    return aliases.get(normalized, normalized)
