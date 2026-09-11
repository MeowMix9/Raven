from __future__ import annotations

from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from raven.infrastructure.models.entities import Quote as QuoteRow
from raven.infrastructure.models.entities import QuoteCalculation as QuoteCalculationRow
from raven.infrastructure.models.entities import QuoteItem as QuoteItemRow
from raven.pricing.pipeline import CalculationLine, CalculationResult, CalculationTraceEntry
from raven.quotes.models import Quote, QuoteItem, QuoteStatus
from raven.quotes.repositories import QuoteRepository
from raven.quotes.snapshot import CalculationSnapshot, PricingValueSnapshot, RuleChangeSnapshot


class SqlAlchemyQuoteRepository(QuoteRepository):
    """SQLAlchemy adapter for the quote domain.

    The persisted calculation snapshot is the historical source of truth for
    the calculation. Normalized quote columns are maintained for querying and
    reporting, while the JSON snapshot preserves the exact inputs and trace.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, quote: Quote) -> None:
        if not quote.items:
            raise ValueError("Quote must contain at least one item")

        for item in quote.items:
            if item.product_id is None:
                raise ValueError(
                    f"Quote item {item.line_number} must reference a product before persistence"
                )

        row = self._session.get(QuoteRow, quote.quote_id)
        if row is None:
            row = QuoteRow(id=quote.quote_id)
            self._session.add(row)

        row.quote_number = quote.quote_number
        row.customer_id = quote.customer_id
        row.created_by_user_id = quote.created_by_user_id
        row.pricing_profile_id = quote.pricing_profile_id
        row.status = quote.status.value.upper()
        row.quote_date = _date_to_datetime(quote.quote_date)
        row.expiration_date = (
            _date_to_datetime(quote.expiration_date) if quote.expiration_date else None
        )
        row.currency = quote.currency
        row.notes = quote.notes

        snapshot = quote.calculation_snapshot
        if snapshot is not None:
            calculation = snapshot.calculation
            row.subtotal = calculation.subtotal_cost
            row.adjustments = calculation.total_price - calculation.subtotal_cost
            row.total_cost = calculation.total_cost
            row.total_price = calculation.total_price
            row.gross_profit = calculation.gross_profit
            row.gross_margin_percent = calculation.gross_margin_percent
            row.calculation_snapshot_json = snapshot.to_dict()
            row.calculation_engine_version = snapshot.engine_version
        else:
            row.calculation_snapshot_json = None
            row.calculation_engine_version = "raven-pricing-v1"

        self._session.flush()
        self._session.execute(
            delete(QuoteCalculationRow).where(QuoteCalculationRow.quote_id == quote.quote_id)
        )
        self._session.execute(delete(QuoteItemRow).where(QuoteItemRow.quote_id == quote.quote_id))

        calculation = snapshot.calculation if snapshot is not None else None
        for item in quote.items:
            calculated_line = _find_calculation_line(calculation, item.line_number)
            self._session.add(
                QuoteItemRow(
                    quote_id=quote.quote_id,
                    line_number=item.line_number,
                    product_id=item.product_id,
                    vendor_product_id=item.vendor_product_id,
                    vendor_id=item.vendor_id,
                    description=item.description,
                    quantity=item.quantity,
                    unit_of_measure=item.unit_of_measure,
                    unit_cost=item.unit_cost,
                    unit_price=(
                        calculated_line.extended_cost / calculated_line.quantity
                        if calculated_line is not None and calculated_line.quantity != 0
                        else item.unit_cost
                    ),
                    extended_cost=item.extended_cost,
                    extended_price=(
                        calculated_line.extended_cost
                        if calculated_line is not None
                        else item.extended_cost
                    ),
                    discount_amount=Decimal("0"),
                    markup_amount=Decimal("0"),
                    margin_amount=Decimal("0"),
                    options_json=dict(item.metadata),
                    calculation_snapshot_json=(
                        snapshot.to_dict() if snapshot is not None else None
                    ),
                )
            )

        if snapshot is not None:
            for sequence, entry in enumerate(snapshot.calculation.trace, start=1):
                self._session.add(
                    QuoteCalculationRow(
                        quote_id=quote.quote_id,
                        quote_item_id=None,
                        calculation_type=entry.action_type,
                        sequence=sequence,
                        input_json={
                            "target": entry.target,
                            "operand_source": entry.operand_source,
                            "operand_key": entry.operand_key,
                            "operand": str(entry.operand),
                            "before": str(entry.before),
                        },
                        output_json={"after": str(entry.after), "label": entry.label},
                        rule_ids_json=[str(entry.rule_id)],
                        pricing_profile_id=snapshot.pricing_profile_id,
                        engine_version=snapshot.engine_version,
                    )
                )

        self._session.flush()

    def get_by_id(self, quote_id: UUID) -> Quote | None:
        row = self._session.get(QuoteRow, quote_id)
        if row is None:
            return None
        return self._to_domain(row)

    def get_by_number(self, quote_number: str) -> Quote | None:
        row = self._session.scalar(
            select(QuoteRow).where(QuoteRow.quote_number == quote_number)
        )
        if row is None:
            return None
        return self._to_domain(row)

    def _to_domain(self, row: QuoteRow) -> Quote:
        item_rows = self._session.scalars(
            select(QuoteItemRow)
            .where(QuoteItemRow.quote_id == row.id)
            .order_by(QuoteItemRow.line_number)
        ).all()

        items = tuple(
            QuoteItem(
                line_number=item.line_number,
                product_id=item.product_id,
                description=item.description,
                quantity=item.quantity,
                unit_of_measure=item.unit_of_measure,
                unit_cost=item.unit_cost,
                extended_cost=item.extended_cost,
                vendor_id=item.vendor_id,
                vendor_product_id=item.vendor_product_id,
                metadata=dict(item.options_json or {}),
            )
            for item in item_rows
        )

        snapshot = _snapshot_from_dict(row.calculation_snapshot_json)
        return Quote(
            quote_id=row.id,
            quote_number=row.quote_number,
            customer_id=row.customer_id,
            created_by_user_id=row.created_by_user_id,
            pricing_profile_id=row.pricing_profile_id,
            quote_date=row.quote_date.date(),
            expiration_date=row.expiration_date.date() if row.expiration_date else None,
            currency=row.currency,
            items=items,
            status=QuoteStatus(row.status.lower()),
            notes=row.notes,
            calculation_snapshot=snapshot,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


def _date_to_datetime(value: date) -> datetime:
    return datetime.combine(value, time.min, tzinfo=timezone.utc)


def _find_calculation_line(
    calculation: CalculationResult | None,
    line_number: int,
) -> CalculationLine | None:
    if calculation is None:
        return None
    index = line_number - 1
    if 0 <= index < len(calculation.lines):
        return calculation.lines[index]
    return None


def _snapshot_from_dict(payload: dict[str, Any] | None) -> CalculationSnapshot | None:
    if not payload:
        return None

    calculation_payload = payload.get("calculation")
    if not isinstance(calculation_payload, dict):
        raise ValueError("Persisted quote snapshot is missing calculation data")

    lines = tuple(
        CalculationLine(
            description=str(line["description"]),
            quantity=Decimal(str(line["quantity"])),
            unit_cost=Decimal(str(line["unit_cost"])),
            extended_cost=Decimal(str(line["extended_cost"])),
        )
        for line in calculation_payload.get("lines", [])
    )
    trace = tuple(
        CalculationTraceEntry(
            rule_id=UUID(entry["rule_id"]),
            action_type=str(entry["action_type"]),
            target=str(entry["target"]),
            operand_source=str(entry["operand_source"]),
            operand_key=entry.get("operand_key"),
            operand=Decimal(str(entry["operand"])),
            before=Decimal(str(entry["before"])),
            after=Decimal(str(entry["after"])),
            label=entry.get("label"),
        )
        for entry in calculation_payload.get("trace", [])
    )
    calculation = CalculationResult(
        lines=lines,
        subtotal_cost=Decimal(str(calculation_payload["subtotal_cost"])),
        total_cost=Decimal(str(calculation_payload["total_cost"])),
        total_price=Decimal(str(calculation_payload["total_price"])),
        gross_profit=Decimal(str(calculation_payload["gross_profit"])),
        gross_margin_percent=Decimal(str(calculation_payload["gross_margin_percent"])),
        applied_rule_ids=tuple(UUID(value) for value in calculation_payload.get("applied_rule_ids", [])),
        trace=trace,
    )

    pricing_values = tuple(
        PricingValueSnapshot(
            key=str(value["key"]),
            value=_deserialize_pricing_value(value.get("value"), value.get("value_type")),
            source_profile_id=UUID(value["source_profile_id"]),
        )
        for value in payload.get("pricing_values", [])
    )
    rule_changes = tuple(
        RuleChangeSnapshot(
            rule_id=UUID(change["rule_id"]),
            action=tuple(
                (str(key), _deserialize_value(value))
                for key, value in dict(change.get("action", {})).items()
            ),
        )
        for change in payload.get("rule_changes", [])
    )

    return CalculationSnapshot(
        pricing_profile_id=UUID(payload["pricing_profile_id"]),
        pricing_profile_version=payload.get("pricing_profile_version"),
        as_of=date.fromisoformat(payload["as_of"]),
        pricing_values=pricing_values,
        applied_rule_ids=tuple(UUID(value) for value in payload.get("applied_rule_ids", [])),
        rule_changes=rule_changes,
        calculation=calculation,
        engine_version=str(payload["engine_version"]),
    )


def _deserialize_pricing_value(value: Any, value_type: str | None) -> Any:
    if value_type == "decimal":
        return Decimal(str(value))
    if value_type == "boolean":
        return bool(value)
    return value


def _deserialize_value(value: Any) -> Any:
    if isinstance(value, list):
        return tuple(_deserialize_value(item) for item in value)
    if isinstance(value, dict):
        return tuple(sorted((str(key), _deserialize_value(item)) for key, item in value.items()))
    return value
