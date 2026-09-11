from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from raven.infrastructure.models.base import Base, TimestampedModel


class User(TimestampedModel):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(200))
    identity_reference: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PricingProfile(TimestampedModel):
    __tablename__ = "pricing_profiles"

    profile_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    profile_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    updated_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))


class Customer(TimestampedModel):
    __tablename__ = "customers"

    customer_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    default_pricing_profile_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("pricing_profiles.id")
    )
    email: Mapped[str | None] = mapped_column(String(320))
    phone: Mapped[str | None] = mapped_column(String(64))
    notes: Mapped[str | None] = mapped_column(Text)
    created_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    updated_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))


class Vendor(TimestampedModel):
    __tablename__ = "vendors"

    vendor_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    contact_name: Mapped[str | None] = mapped_column(String(200))
    contact_email: Mapped[str | None] = mapped_column(String(320))
    contact_phone: Mapped[str | None] = mapped_column(String(64))
    website: Mapped[str | None] = mapped_column(String(500))
    notes: Mapped[str | None] = mapped_column(Text)
    created_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    updated_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))


class Product(TimestampedModel):
    __tablename__ = "products"

    product_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    sku: Mapped[str | None] = mapped_column(String(128))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(100))
    unit_of_measure: Mapped[str] = mapped_column(String(32), default="EA")
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)


class VendorProduct(TimestampedModel):
    __tablename__ = "vendor_products"

    vendor_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("vendors.id"), nullable=False)
    product_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    vendor_sku: Mapped[str] = mapped_column(String(128), nullable=False)
    vendor_product_name: Mapped[str | None] = mapped_column(String(200))
    vendor_description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    lead_time_days: Mapped[int | None] = mapped_column(Integer)
    minimum_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)


class PricingProfileAssignment(TimestampedModel):
    __tablename__ = "pricing_profile_assignments"

    pricing_profile_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("pricing_profiles.id"), nullable=False
    )
    scope_type: Mapped[str] = mapped_column(String(32), nullable=False)
    scope_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    priority: Mapped[int] = mapped_column(Integer, default=0)
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class PricingValue(TimestampedModel):
    __tablename__ = "pricing_values"

    pricing_profile_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("pricing_profiles.id"), nullable=False
    )
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    value_type: Mapped[str] = mapped_column(String(32), nullable=False)
    numeric_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    text_value: Mapped[str | None] = mapped_column(Text)
    boolean_value: Mapped[bool | None] = mapped_column(Boolean)
    unit: Mapped[str | None] = mapped_column(String(32))
    currency: Mapped[str | None] = mapped_column(String(3))
    minimum_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    maximum_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class PricingRule(TimestampedModel):
    __tablename__ = "pricing_rules"

    pricing_profile_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("pricing_profiles.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    condition_group_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    action_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    updated_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))


class Quote(TimestampedModel):
    __tablename__ = "quotes"

    quote_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    customer_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    pricing_profile_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("pricing_profiles.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), default="DRAFT")
    quote_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expiration_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=Decimal("0"))
    adjustments: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=Decimal("0"))
    total_cost: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=Decimal("0"))
    total_price: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=Decimal("0"))
    gross_profit: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=Decimal("0"))
    gross_margin_percent: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=Decimal("0"))
    notes: Mapped[str | None] = mapped_column(Text)
    calculation_snapshot_json: Mapped[dict | None] = mapped_column(JSONB)
    calculation_engine_version: Mapped[str] = mapped_column(String(32), default="0.1.0")


class QuoteItem(TimestampedModel):
    __tablename__ = "quote_items"

    quote_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("quotes.id", ondelete="CASCADE"), nullable=False)
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    product_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    vendor_product_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("vendor_products.id"))
    vendor_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("vendors.id"))
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unit_of_measure: Mapped[str] = mapped_column(String(32), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    extended_cost: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    extended_price: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=Decimal("0"))
    markup_amount: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=Decimal("0"))
    margin_amount: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=Decimal("0"))
    options_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    calculation_snapshot_json: Mapped[dict | None] = mapped_column(JSONB)


class QuoteCalculation(TimestampedModel):
    __tablename__ = "quote_calculations"

    quote_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("quotes.id", ondelete="CASCADE"), nullable=False)
    quote_item_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("quote_items.id", ondelete="CASCADE")
    )
    calculation_type: Mapped[str] = mapped_column(String(32), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    input_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    output_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    rule_ids_json: Mapped[list] = mapped_column(JSONB, default=list)
    pricing_profile_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("pricing_profiles.id"), nullable=False
    )
    engine_version: Mapped[str] = mapped_column(String(32), nullable=False)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    before_json: Mapped[dict | None] = mapped_column(JSONB)
    after_json: Mapped[dict | None] = mapped_column(JSONB)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
