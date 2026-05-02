"""add_audit_results_table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-20 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("brand_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("brands.id"), nullable=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("recommendations", postgresql.JSONB(), nullable=False),
        sa.Column("schema_suggestions", postgresql.JSONB(), nullable=True),
        sa.Column("llms_txt_content", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_audit_results_url_ts", "audit_results", ["url", "created_at"])
    op.create_index("ix_audit_results_brand", "audit_results", ["brand_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_results_brand", table_name="audit_results")
    op.drop_index("ix_audit_results_url_ts", table_name="audit_results")
    op.drop_table("audit_results")
