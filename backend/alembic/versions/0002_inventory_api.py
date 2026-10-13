"""Add inventory snapshots and API clients.

Revision ID: 0002_inventory_api
Revises: 0001_initial
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_inventory_api"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "inventory_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("items_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_inventory_snapshots_created_at",
        "inventory_snapshots",
        ["created_at"],
    )
    op.create_table(
        "inventory_api_clients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("api_key_hash", sa.String(64), nullable=False),
        sa.Column("minimum_quantity_available", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("client_code", name="uq_inventory_api_clients_client_code"),
        sa.UniqueConstraint("api_key_hash", name="uq_inventory_api_clients_api_key_hash"),
    )


def downgrade() -> None:
    op.drop_table("inventory_api_clients")
    op.drop_index("ix_inventory_snapshots_created_at", table_name="inventory_snapshots")
    op.drop_table("inventory_snapshots")
