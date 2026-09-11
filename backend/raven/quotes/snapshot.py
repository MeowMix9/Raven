from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from raven.pricing.pipeline import CalculationResult
from raven.pricing.rules import RuleEvaluationResult
from raven.pricing.resolver import ResolvedPricingContext


@dataclass(frozen=True, slots=True)
class PricingValueSnapshot:
    key: str
    value: Decimal | str | bool
    source_profile_id: UUID

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "value": _serialize_value(self.value),
            "value_type": _value_type(self.value),
            "source_profile_id": str(self.source_profile_id),
        }


@dataclass(frozen=True, slots=True)
class RuleChangeSnapshot:
    rule_id: UUID
    action: tuple[tuple[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": str(self.rule_id),
            "action": {key: _serialize_value(value) for key, value in self.action},
        }


@dataclass(frozen=True, slots=True)
class CalculationSnapshot:
    """Immutable historical record of the inputs and result of a quote calculation.

    The snapshot deliberately contains value copies rather than references to
    live pricing configuration. Once created, later pricing/profile/rule changes
    cannot alter the historical calculation represented by this object.
    """

    pricing_profile_id: UUID
    pricing_profile_version: int | None
    as_of: date
    pricing_values: tuple[PricingValueSnapshot, ...]
    applied_rule_ids: tuple[UUID, ...]
    rule_changes: tuple[RuleChangeSnapshot, ...]
    calculation: CalculationResult
    engine_version: str

    @classmethod
    def from_calculation(
        cls,
        *,
        pricing: ResolvedPricingContext,
        rules: RuleEvaluationResult,
        calculation: CalculationResult,
        engine_version: str,
        pricing_profile_version: int | None = None,
    ) -> "CalculationSnapshot":
        if not engine_version.strip():
            raise ValueError("Calculation engine version cannot be blank")

        pricing_values = tuple(
            PricingValueSnapshot(
                key=value.key,
                value=value.value,
                source_profile_id=value.source_profile_id,
            )
            for value in pricing.values
        )

        if len(rules.applied_rule_ids) != len(rules.changes):
            raise ValueError("Applied rule IDs and rule changes must have matching lengths")

        rule_changes = tuple(
            RuleChangeSnapshot(
                rule_id=rule_id,
                action=tuple(sorted((key, _freeze_value(value)) for key, value in change.items())),
            )
            for rule_id, change in zip(rules.applied_rule_ids, rules.changes, strict=True)
        )

        return cls(
            pricing_profile_id=pricing.profile_id,
            pricing_profile_version=pricing_profile_version,
            as_of=pricing.as_of,
            pricing_values=pricing_values,
            applied_rule_ids=tuple(rules.applied_rule_ids),
            rule_changes=rule_changes,
            calculation=calculation,
            engine_version=engine_version.strip(),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible representation suitable for persistence."""
        return {
            "pricing_profile_id": str(self.pricing_profile_id),
            "pricing_profile_version": self.pricing_profile_version,
            "as_of": self.as_of.isoformat(),
            "pricing_values": [value.to_dict() for value in self.pricing_values],
            "applied_rule_ids": [str(rule_id) for rule_id in self.applied_rule_ids],
            "rule_changes": [change.to_dict() for change in self.rule_changes],
            "calculation": _calculation_to_dict(self.calculation),
            "engine_version": self.engine_version,
        }


def _freeze_value(value: Any) -> Any:
    if isinstance(value, dict):
        return tuple(sorted((str(key), _freeze_value(item)) for key, item in value.items()))
    if isinstance(value, list):
        return tuple(_freeze_value(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_freeze_value(item) for item in value)
    return value


def _value_type(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, Decimal):
        return "decimal"
    if isinstance(value, str):
        return "string"
    return type(value).__name__


def _serialize_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, tuple):
        if value and all(isinstance(item, tuple) and len(item) == 2 for item in value):
            return {str(key): _serialize_value(item) for key, item in value}
        return [_serialize_value(item) for item in value]
    if isinstance(value, list):
        return [_serialize_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _serialize_value(item) for key, item in value.items()}
    return value


def _calculation_to_dict(calculation: CalculationResult) -> dict[str, Any]:
    return {
        "lines": [
            {
                "description": line.description,
                "quantity": str(line.quantity),
                "unit_cost": str(line.unit_cost),
                "extended_cost": str(line.extended_cost),
            }
            for line in calculation.lines
        ],
        "subtotal_cost": str(calculation.subtotal_cost),
        "total_cost": str(calculation.total_cost),
        "total_price": str(calculation.total_price),
        "gross_profit": str(calculation.gross_profit),
        "gross_margin_percent": str(calculation.gross_margin_percent),
        "applied_rule_ids": [str(rule_id) for rule_id in calculation.applied_rule_ids],
        "trace": [
            {
                "rule_id": str(entry.rule_id),
                "action_type": entry.action_type,
                "target": entry.target,
                "operand_source": entry.operand_source,
                "operand_key": entry.operand_key,
                "operand": str(entry.operand),
                "before": str(entry.before),
                "after": str(entry.after),
                "label": entry.label,
            }
            for entry in calculation.trace
        ],
    }
