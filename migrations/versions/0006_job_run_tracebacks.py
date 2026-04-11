"""job run tracebacks

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-10 00:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("job_runs", sa.Column("traceback", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("job_runs", "traceback")
