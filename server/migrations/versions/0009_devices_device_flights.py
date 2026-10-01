"""Pi devices and device-submitted flight requests

Revision ID: 0009devices
Revises: 0008username
Create Date: 2026-10-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0009devices"
down_revision: Union[str, None] = "0008username"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("devices"):
        op.create_table(
            "devices",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("name", sa.String(length=80), nullable=False, unique=True),
            sa.Column("key_encrypted", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        )
    columns = {column["name"] for column in inspector.get_columns("simulated_flight_requests")}
    with op.batch_alter_table("simulated_flight_requests") as batch:
        batch.alter_column("submitter_user_id", existing_type=sa.String(length=36), nullable=True)
        if "device_id" not in columns:
            batch.add_column(sa.Column("device_id", sa.String(length=36), nullable=True))
            batch.add_column(sa.Column("client_ref", sa.String(length=64), nullable=True))
            batch.create_index("ix_simulated_flight_requests_device_id", ["device_id"])
            batch.create_foreign_key("fk_flight_device", "devices", ["device_id"], ["id"], ondelete="SET NULL")
            batch.create_unique_constraint("uq_flight_device_client_ref", ["device_id", "client_ref"])


def downgrade() -> None:
    with op.batch_alter_table("simulated_flight_requests") as batch:
        batch.drop_constraint("uq_flight_device_client_ref", type_="unique")
        batch.drop_constraint("fk_flight_device", type_="foreignkey")
        batch.drop_index("ix_simulated_flight_requests_device_id")
        batch.drop_column("client_ref")
        batch.drop_column("device_id")
    op.drop_table("devices")
