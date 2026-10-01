"""add profile and licence fields with verified profile-update challenges

Revision ID: c8e1a7d49b32
Revises: e6c7d8f9a0b1
Create Date: 2026-10-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c8e1a7d49b32"
down_revision: Union[str, None] = "e6c7d8f9a0b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("full_name", sa.String(length=200), nullable=True))
    op.add_column("users", sa.Column("license_code", sa.String(length=100), nullable=True))
    op.add_column("users", sa.Column("license_class", sa.String(length=1), nullable=True))
    op.add_column("users", sa.Column("license_expiry", sa.Date(), nullable=True))
    op.create_table(
        "profile_update_challenges",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", sa.String(length=36), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("current_email_challenge_id", sa.String(length=36), sa.ForeignKey("email_challenges.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("new_email_challenge_id", sa.String(length=36), sa.ForeignKey("email_challenges.id", ondelete="SET NULL"), nullable=True, unique=True),
        sa.Column("original_email", sa.String(length=320), nullable=False),
        sa.Column("requested_email", sa.String(length=320), nullable=False),
        sa.Column("changes_ciphertext", sa.Text(), nullable=False),
        sa.Column("credential_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("current_email_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_profile_update_challenges_user_id", "profile_update_challenges", ["user_id"])
    op.create_index("ix_profile_update_challenges_session_id", "profile_update_challenges", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_profile_update_challenges_session_id", table_name="profile_update_challenges")
    op.drop_index("ix_profile_update_challenges_user_id", table_name="profile_update_challenges")
    op.drop_table("profile_update_challenges")
    op.drop_column("users", "license_expiry")
    op.drop_column("users", "license_class")
    op.drop_column("users", "license_code")
    op.drop_column("users", "full_name")
