"""encrypted flight request details

Revision ID: d4a7f1c8e2b0
Revises: a71e8c4b2d90
Create Date: 2026-09-30
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4a7f1c8e2b0"
down_revision: Union[str, None] = "a71e8c4b2d90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("simulated_flight_requests")}
    if "request_details_ciphertext" not in columns:
        op.add_column("simulated_flight_requests", sa.Column("request_details_ciphertext", sa.Text(), nullable=False, server_default="{}"))
    if "request_payload_digest" not in columns:
        op.add_column("simulated_flight_requests", sa.Column("request_payload_digest", sa.String(length=128), nullable=False, server_default=""))


def downgrade() -> None:
    op.drop_column("simulated_flight_requests", "request_payload_digest")
    op.drop_column("simulated_flight_requests", "request_details_ciphertext")
