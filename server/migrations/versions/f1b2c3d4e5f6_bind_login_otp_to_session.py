"""bind login OTP challenges to their staged session

Revision ID: f1b2c3d4e5f6
Revises: d4a7f1c8e2b0
Create Date: 2026-09-30
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f1b2c3d4e5f6"
down_revision: Union[str, None] = "d4a7f1c8e2b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("email_challenges")}
    if "session_id" not in columns:
        op.add_column("email_challenges", sa.Column("session_id", sa.String(length=36), nullable=True))
        op.create_index("ix_email_challenges_session_id", "email_challenges", ["session_id"], unique=False)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    indexes = {index["name"] for index in inspector.get_indexes("email_challenges")}
    if "ix_email_challenges_session_id" in indexes:
        op.drop_index("ix_email_challenges_session_id", table_name="email_challenges")
    columns = {column["name"] for column in inspector.get_columns("email_challenges")}
    if "session_id" in columns:
        op.drop_column("email_challenges", "session_id")
