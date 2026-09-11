from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from raven.infrastructure.models.entities import PricingProfile, PricingProfileAssignment, PricingRule, PricingValue
from raven.pricing.models import ResolvedPricingValue
from raven.pricing.profile_selection import PricingProfileCandidate, select_pricing_profile
from raven.pricing.rules import PricingRule as DomainPricingRule
from raven.pricing.value_resolution import PricingValueCandidate, resolve_pricing_values


class SqlAlchemyPricingRepository:
    """SQLAlchemy adapter for the pure pricing-domain services."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def resolve_profile_id(
        self,
        *,
        requested_profile_id: UUID,
        customer_id: UUID | None,
        product_id: UUID | None,
        as_of: date,
    ) -> UUID:
        assignments = self._session.scalars(
            select(PricingProfileAssignment).where(
                PricingProfileAssignment.pricing_profile_id.is_not(None)
            )
        ).all()
        profiles = {
            profile.id: profile
            for profile in self._session.scalars(select(PricingProfile)).all()
        }

        candidates: list[PricingProfileCandidate] = []
        for assignment in assignments:
            profile = profiles.get(assignment.pricing_profile_id)
            if profile is None:
                continue
            if assignment.scope_type.upper() == "CUSTOMER" and assignment.scope_id != customer_id:
                continue
            if assignment.scope_type.upper() == "PRODUCT" and assignment.scope_id != product_id:
                continue
            if assignment.scope_type.upper() in {"DEFAULT", "GLOBAL"} and assignment.scope_id is not None:
                continue
            if assignment.scope_type.upper() not in {"CUSTOMER", "PRODUCT", "DEFAULT", "GLOBAL"}:
                continue

            candidates.append(
                PricingProfileCandidate(
                    profile_id=profile.id,
                    scope_type=assignment.scope_type,
                    scope_id=assignment.scope_id,
                    assignment_priority=assignment.priority,
                    profile_priority=profile.priority,
                    assignment_effective_from=_to_date(assignment.effective_from),
                    assignment_effective_to=_to_date(assignment.effective_to),
                    profile_effective_from=_to_date(profile.effective_from),
                    profile_effective_to=_to_date(profile.effective_to),
                    profile_version=profile.version,
                    assignment_is_active=assignment.is_active,
                    profile_is_active=profile.is_active,
                )
            )

        # The explicitly requested profile remains available as a fallback only
        # when it has no assignment candidate. This preserves the API contract
        # while keeping selection deterministic and configuration-driven.
        if not candidates:
            profile = profiles.get(requested_profile_id)
            if profile is not None:
                candidates.append(
                    PricingProfileCandidate(
                        profile_id=profile.id,
                        scope_type="DEFAULT",
                        scope_id=None,
                        assignment_priority=0,
                        profile_priority=profile.priority,
                        assignment_effective_from=None,
                        assignment_effective_to=None,
                        profile_effective_from=_to_date(profile.effective_from),
                        profile_effective_to=_to_date(profile.effective_to),
                        profile_version=profile.version,
                        assignment_is_active=True,
                        profile_is_active=profile.is_active,
                    )
                )

        return select_pricing_profile(tuple(candidates), as_of=as_of).profile_id

    def get_values(
        self,
        *,
        profile_id: UUID,
        as_of: date,
        quantity: Decimal | None = None,
    ) -> tuple[ResolvedPricingValue, ...]:
        rows = self._session.scalars(
            select(PricingValue).where(PricingValue.pricing_profile_id == profile_id)
        ).all()

        candidates = tuple(
            PricingValueCandidate(
                id=row.id,
                profile_id=row.pricing_profile_id,
                key=row.key,
                value=_value_from_row(row),
                value_type=row.value_type,
                minimum_quantity=row.minimum_quantity,
                maximum_quantity=row.maximum_quantity,
                effective_from=_to_date(row.effective_from),
                effective_to=_to_date(row.effective_to),
                is_active=row.is_active,
            )
            for row in rows
        )
        return resolve_pricing_values(candidates, as_of=as_of, quantity=quantity)

    def get_rules(
        self,
        *,
        profile_id: UUID,
        as_of: date,
    ) -> tuple[DomainPricingRule, ...]:
        rows = self._session.scalars(
            select(PricingRule).where(PricingRule.pricing_profile_id == profile_id)
        ).all()

        return tuple(
            DomainPricingRule(
                id=row.id,
                name=row.name,
                priority=row.priority,
                condition_group=dict(row.condition_group_json or {}),
                action=dict(row.action_json or {}),
                is_enabled=row.is_enabled and _date_range_contains(
                    as_of,
                    _to_date(row.effective_from),
                    _to_date(row.effective_to),
                ),
            )
            for row in rows
        )


def _value_from_row(row: PricingValue) -> Decimal | str | bool:
    value_type = row.value_type.upper()
    if value_type == "NUMERIC" and row.numeric_value is not None:
        return row.numeric_value
    if value_type == "TEXT" and row.text_value is not None:
        return row.text_value
    if value_type == "BOOLEAN" and row.boolean_value is not None:
        return row.boolean_value
    raise ValueError(f"Pricing value '{row.key}' has no value for type {row.value_type}")


def _to_date(value) -> date | None:
    return value.date() if value is not None else None


def _date_range_contains(value: date, effective_from: date | None, effective_to: date | None) -> bool:
    if effective_from is not None and effective_from > value:
        return False
    if effective_to is not None and effective_to <= value:
        return False
    return True
