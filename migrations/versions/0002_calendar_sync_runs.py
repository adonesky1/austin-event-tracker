"""calendar sync runs

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-22 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    syncrunstatus = postgresql.ENUM(
        "success",
        "failed",
        "skipped",
        name="syncrunstatus",
    )
    syncrunstatus.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "calendar_sync_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("trigger", sa.String(50), nullable=False, server_default="scheduler"),
        sa.Column(
            "status",
            sa.Enum("success", "failed", "skipped", name="syncrunstatus"),
            nullable=False,
            server_default="success",
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("window_start", sa.Date(), nullable=False),
        sa.Column("window_end", sa.Date(), nullable=False),
        sa.Column("selected_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deleted_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("calendar_sync_runs")
    postgresql.ENUM(name="syncrunstatus").drop(op.get_bind(), checkfirst=True)
