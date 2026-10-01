"""username login and optional email for the default owner

Revision ID: 0008username
Revises: c8e1a7d49b32
Create Date: 2026-10-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0008username"
down_revision: Union[str, None] = "c8e1a7d49b32"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("users")}
    with op.batch_alter_table("users") as batch:
        if "username" not in columns:
            batch.add_column(sa.Column("username", sa.String(length=32), nullable=True))
            batch.create_index("ix_users_username", ["username"], unique=True)
        batch.alter_column("email_normalized", existing_type=sa.String(length=320), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_index("ix_users_username")
        batch.drop_column("username")
