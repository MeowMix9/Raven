"""Domain-level types and enums shared across Raven services.

This module defines vocabulary and data-shape conventions only. It must not
contain business-specific pricing values or customer-specific configuration.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from enum import StrEnum


class QuoteStatus(StrEnum):
    DRAFT = "draft"
    CALCULATED = "calculated"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    SENT = "sent"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class PricingProfileType(StrEnum):
    DEFAULT = "default"
    CUSTOMER = "customer"
    WHOLESALE = "wholesale"
    RETAIL = "retail"
    PROMOTIONAL = "promotional"
    CUSTOM = "custom"


class PricingValueType(StrEnum):
    NUMBER = "number"
    TEXT = "text"
    BOOLEAN = "boolean"


class PricingScopeType(StrEnum):
    GLOBAL = "global"
    CUSTOMER = "customer"
    VENDOR = "vendor"
    PRODUCT = "product"
    PRODUCT_CATEGORY = "product_category"
    QUOTE = "quote"


class AuditActorType(StrEnum):
    USER = "user"
    SYSTEM = "system"
    API = "api"
    JOB = "job"


class CalculationStage(StrEnum):
    RESOLVE_PROFILE = "resolve_profile"
    RESOLVE_VALUES = "resolve_values"
    EVALUATE_RULES = "evaluate_rules"
    CALCULATE_COST = "calculate_cost"
    APPLY_MARKUP = "apply_markup"
    APPLY_DISCOUNTS = "apply_discounts"
    APPLY_FEES = "apply_fees"
    APPLY_MINIMUMS = "apply_minimums"
    ROUND = "round"
    CALCULATE_MARGIN = "calculate_margin"


MONEY_QUANTUM = Decimal("0.01")


def quantize_money(value: Decimal) -> Decimal:
    """Round a Decimal monetary value using the Raven money policy."""

    if not isinstance(value, Decimal):
        raise TypeError("Monetary values must be Decimal instances")
    return value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
