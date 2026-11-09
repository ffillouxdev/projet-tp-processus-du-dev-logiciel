"""add match score reports and validation status

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-09 15:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("matches", sa.Column("player1_reported_score_p1", sa.Integer(), nullable=True))
    op.add_column("matches", sa.Column("player1_reported_score_p2", sa.Integer(), nullable=True))
    op.add_column("matches", sa.Column("player2_reported_score_p1", sa.Integer(), nullable=True))
    op.add_column("matches", sa.Column("player2_reported_score_p2", sa.Integer(), nullable=True))
    op.alter_column(
        "matches",
        "status",
        existing_type=sa.String(length=20),
        type_=sa.String(length=30),
        existing_nullable=False,
        existing_server_default="pending",
    )


def downgrade() -> None:
    op.alter_column(
        "matches",
        "status",
        existing_type=sa.String(length=30),
        type_=sa.String(length=20),
        existing_nullable=False,
        existing_server_default="pending",
    )
    op.drop_column("matches", "player2_reported_score_p2")
    op.drop_column("matches", "player2_reported_score_p1")
    op.drop_column("matches", "player1_reported_score_p2")
    op.drop_column("matches", "player1_reported_score_p1")
