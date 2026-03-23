"""admin config and tracking

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-22 00:00:01.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    trackeditemkind = postgresql.ENUM(
        "artist",
        "venue",
        "keyword",
        "series",
        name="trackeditemkind",
    )
    trackeditemkind.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "prompt_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("key", sa.String(100), nullable=False, unique=True),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("user_prompt_template", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "tracked_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("artist", "venue", "keyword", "series", name="trackeditemkind"),
            nullable=False,
        ),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("boost_weight", sa.Float(), nullable=False, server_default="0.15"),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("tracked_items")
    op.drop_table("prompt_configs")
    postgresql.ENUM(name="trackeditemkind").drop(op.get_bind(), checkfirst=True)
