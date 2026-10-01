"""prevent duplicate open role requests and active capability grants

Revision ID: e6c7d8f9a0b1
Revises: f1b2c3d4e5f6
Create Date: 2026-10-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e6c7d8f9a0b1"
down_revision: Union[str, None] = "f1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "uq_role_elevation_pending_target",
        "role_elevation_requests",
        ["requester_user_id", "requested_role"],
        unique=True,
        sqlite_where=sa.text("status = 'PENDING'"),
        postgresql_where=sa.text("status = 'PENDING'"),
    )
    op.create_index(
        "uq_active_capability_grant_target",
        "capability_grants",
        ["grantee_user_id", "resource_scope"],
        unique=True,
        sqlite_where=sa.text("revoked_at IS NULL"),
        postgresql_where=sa.text("revoked_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_active_capability_grant_target", table_name="capability_grants")
    op.drop_index("uq_role_elevation_pending_target", table_name="role_elevation_requests")
