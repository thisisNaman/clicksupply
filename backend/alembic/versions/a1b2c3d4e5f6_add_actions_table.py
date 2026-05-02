"""add_actions_table

Revision ID: a1b2c3d4e5f6
Revises: 377eadef8bbe
Create Date: 2026-04-19 22:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "377eadef8bbe"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("brand_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("brands.id"), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("impact", sa.String(20), server_default="medium"),
        sa.Column("effort", sa.String(20), server_default="medium"),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("priority_rank", sa.Integer(), server_default="0"),
        sa.Column("action_type", sa.String(50), nullable=True),
        sa.Column("engine", sa.String(50), nullable=True),
        sa.Column("prompt_text", sa.Text(), nullable=True),
        sa.Column("prompt_id", sa.String(36), nullable=True),
        sa.Column("current_mention_rate", sa.Float(), nullable=True),
        sa.Column("current_rate", sa.Float(), nullable=True),
        sa.Column("suggested_content", sa.Text(), nullable=True),
        sa.Column("suggested_schema", sa.Text(), nullable=True),
        sa.Column("verification_type", sa.String(30), nullable=True),
        sa.Column("baseline_value", sa.Float(), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_value", sa.Float(), nullable=True),
        sa.Column("verification_status", sa.String(20), nullable=True),
        sa.Column("crawler_type", sa.String(50), nullable=True),
        sa.Column("audit_category", sa.String(50), nullable=True),
        sa.Column("audit_severity", sa.String(20), nullable=True),
        sa.Column("engines_missing", postgresql.JSONB(), nullable=True),
        sa.Column("engines_citing", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_actions_brand_status", "actions", ["brand_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_actions_brand_status", table_name="actions")
    op.drop_table("actions")
