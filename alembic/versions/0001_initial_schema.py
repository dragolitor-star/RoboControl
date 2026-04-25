"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-04-25 00:00:00

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "robot_types",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("description", sa.String(length=200), nullable=True),
        sa.Column("rcs_task_type", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.UniqueConstraint("name", name="uq_robot_types_name"),
    )
    op.create_index("ix_robot_types_name", "robot_types", ["name"])
    op.create_index("ix_robot_types_rcs_task_type", "robot_types", ["rcs_task_type"])
    op.create_index("ix_robot_types_name_rcs", "robot_types", ["name", "rcs_task_type"])

    op.create_table(
        "task_history",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("robot_task_code", sa.String(length=100), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "running",
                "completed",
                "failed",
                "cancelled",
                name="task_status_enum",
            ),
            nullable=False,
        ),
        sa.Column("robot_code", sa.String(length=50), nullable=True),
        sa.Column("source_code", sa.String(length=100), nullable=True),
        sa.Column("target_code", sa.String(length=100), nullable=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
        sa.Column("start_time", sa.DateTime(), nullable=True),
        sa.Column("end_time", sa.DateTime(), nullable=True),
        sa.Column("error_msg", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.UniqueConstraint("robot_task_code", name="uq_task_history_robot_task_code"),
        sa.UniqueConstraint("idempotency_key", name="uq_task_history_idempotency_key"),
    )
    op.create_index("ix_task_history_robot_task_code", "task_history", ["robot_task_code"])
    op.create_index("ix_task_history_status", "task_history", ["status"])
    op.create_index("ix_task_history_robot_code", "task_history", ["robot_code"])
    op.create_index("ix_task_history_idempotency_key", "task_history", ["idempotency_key"])


def downgrade() -> None:
    op.drop_index("ix_task_history_idempotency_key", table_name="task_history")
    op.drop_index("ix_task_history_robot_code", table_name="task_history")
    op.drop_index("ix_task_history_status", table_name="task_history")
    op.drop_index("ix_task_history_robot_task_code", table_name="task_history")
    op.drop_table("task_history")

    op.drop_index("ix_robot_types_name_rcs", table_name="robot_types")
    op.drop_index("ix_robot_types_rcs_task_type", table_name="robot_types")
    op.drop_index("ix_robot_types_name", table_name="robot_types")
    op.drop_table("robot_types")
