"""owner granted admin capability grants

Revision ID: a71e8c4b2d90
Revises: 9c4f2d7e6a11
Create Date: 2026-09-22
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a71e8c4b2d90"
down_revision: Union[str, None] = "9c4f2d7e6a11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "capability_grants",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("grantor_user_id", sa.String(length=36), nullable=False),
        sa.Column("grantee_user_id", sa.String(length=36), nullable=False),
        sa.Column("actions_json", sa.String(length=300), nullable=False),
        sa.Column("resource_scope", sa.String(length=80), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("revoked_reason", sa.String(length=500), nullable=True),
        sa.CheckConstraint("resource_scope = 'PC_GUEST'", name="ck_capability_grant_scope"),
        sa.ForeignKeyConstraint(["grantor_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["grantee_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["revoked_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_capability_grants_grantor_user_id", "capability_grants", ["grantor_user_id"])
    op.create_index("ix_capability_grants_grantee_user_id", "capability_grants", ["grantee_user_id"])
    op.create_index("ix_capability_grants_revoked_by_user_id", "capability_grants", ["revoked_by_user_id"])


def downgrade() -> None:
    op.drop_index("ix_capability_grants_revoked_by_user_id", table_name="capability_grants")
    op.drop_index("ix_capability_grants_grantee_user_id", table_name="capability_grants")
    op.drop_index("ix_capability_grants_grantor_user_id", table_name="capability_grants")
    op.drop_table("capability_grants")
