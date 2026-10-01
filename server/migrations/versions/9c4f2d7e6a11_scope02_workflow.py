"""scope02 workflow, account review and read-only fake adapter

Revision ID: 9c4f2d7e6a11
Revises: 380891b589d3
Create Date: 2026-09-22
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9c4f2d7e6a11"
down_revision: Union[str, None] = "380891b589d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("version", sa.Integer(), nullable=False, server_default="1"))

    op.create_table(
        "role_elevation_requests",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("requester_user_id", sa.String(length=36), nullable=False),
        sa.Column("requested_role", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("reviewer_user_id", sa.String(length=36), nullable=True),
        sa.Column("reviewer_reason", sa.String(length=500), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("requested_role IN ('OPERATOR', 'ADMIN')", name="ck_role_elevation_target"),
        sa.CheckConstraint("status IN ('PENDING', 'APPROVED', 'REJECTED', 'CANCELLED')", name="ck_role_elevation_status"),
        sa.ForeignKeyConstraint(["requester_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewer_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_role_elevation_requests_requester_user_id", "role_elevation_requests", ["requester_user_id"])
    op.create_index("ix_role_elevation_requests_reviewer_user_id", "role_elevation_requests", ["reviewer_user_id"])
    op.create_index("ix_role_elevation_requests_status", "role_elevation_requests", ["status"])

    op.create_table(
        "simulated_flight_requests",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("submitter_user_id", sa.String(length=36), nullable=False),
        sa.Column("summary", sa.String(length=240), nullable=False),
        sa.Column("scheduled_start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scheduled_end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("simulated_geometry_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("simulated", sa.Boolean(), nullable=False),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('DRAFT', 'SUBMITTED', 'UNDER_REVIEW', 'NEEDS_INFORMATION', 'REJECTED', 'APPROVED_SIMULATED')", name="ck_simulated_request_status"),
        sa.CheckConstraint("simulated = 1", name="ck_simulated_request_flag"),
        sa.ForeignKeyConstraint(["submitter_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_simulated_flight_requests_submitter_user_id", "simulated_flight_requests", ["submitter_user_id"])
    op.create_index("ix_simulated_flight_requests_status", "simulated_flight_requests", ["status"])

    op.create_table(
        "idempotency_records",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("actor_user_id", sa.String(length=36), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("object_type", sa.String(length=80), nullable=False),
        sa.Column("object_id", sa.String(length=36), nullable=True),
        sa.Column("payload_digest", sa.String(length=128), nullable=False),
        sa.Column("response_json", sa.Text(), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("actor_user_id", "idempotency_key", name="uq_idempotency_actor_key"),
    )
    op.create_index("ix_idempotency_records_actor_user_id", "idempotency_records", ["actor_user_id"])
    op.create_index("ix_idempotency_records_object_id", "idempotency_records", ["object_id"])

    op.create_table(
        "workflow_history",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("actor_user_id", sa.String(length=36), nullable=True),
        sa.Column("object_type", sa.String(length=80), nullable=False),
        sa.Column("object_id", sa.String(length=36), nullable=False),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("from_state", sa.String(length=32), nullable=True),
        sa.Column("to_state", sa.String(length=32), nullable=True),
        sa.Column("from_version", sa.Integer(), nullable=True),
        sa.Column("to_version", sa.Integer(), nullable=True),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("metadata_redacted", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workflow_history_actor_user_id", "workflow_history", ["actor_user_id"])
    op.create_index("ix_workflow_history_object_type", "workflow_history", ["object_type"])
    op.create_index("ix_workflow_history_object_id", "workflow_history", ["object_id"])
    op.create_index("ix_workflow_history_request_id", "workflow_history", ["request_id"])


def downgrade() -> None:
    op.drop_index("ix_workflow_history_request_id", table_name="workflow_history")
    op.drop_index("ix_workflow_history_object_id", table_name="workflow_history")
    op.drop_index("ix_workflow_history_object_type", table_name="workflow_history")
    op.drop_index("ix_workflow_history_actor_user_id", table_name="workflow_history")
    op.drop_table("workflow_history")
    op.drop_index("ix_idempotency_records_object_id", table_name="idempotency_records")
    op.drop_index("ix_idempotency_records_actor_user_id", table_name="idempotency_records")
    op.drop_table("idempotency_records")
    op.drop_index("ix_simulated_flight_requests_status", table_name="simulated_flight_requests")
    op.drop_index("ix_simulated_flight_requests_submitter_user_id", table_name="simulated_flight_requests")
    op.drop_table("simulated_flight_requests")
    op.drop_index("ix_role_elevation_requests_status", table_name="role_elevation_requests")
    op.drop_index("ix_role_elevation_requests_reviewer_user_id", table_name="role_elevation_requests")
    op.drop_index("ix_role_elevation_requests_requester_user_id", table_name="role_elevation_requests")
    op.drop_table("role_elevation_requests")
    op.drop_column("users", "version")
