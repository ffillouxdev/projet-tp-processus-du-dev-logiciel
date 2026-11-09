"""add matches table for tournament brackets

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-09 13:40:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "matches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tournament_id", sa.Integer(), nullable=False),
        sa.Column("round_number", sa.Integer(), nullable=False),
        sa.Column("round_name", sa.String(length=50), nullable=False),
        sa.Column("match_order", sa.Integer(), nullable=False),
        sa.Column("player1_id", sa.Integer(), nullable=True),
        sa.Column("player2_id", sa.Integer(), nullable=True),
        sa.Column("winner_id", sa.Integer(), nullable=True),
        sa.Column("score_player1", sa.Integer(), nullable=True),
        sa.Column("score_player2", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("next_match_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["next_match_id"], ["matches.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["player1_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["player2_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tournament_id"], ["tournaments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["winner_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_matches_id"), "matches", ["id"], unique=False)
    op.create_index(op.f("ix_matches_next_match_id"), "matches", ["next_match_id"], unique=False)
    op.create_index(op.f("ix_matches_player1_id"), "matches", ["player1_id"], unique=False)
    op.create_index(op.f("ix_matches_player2_id"), "matches", ["player2_id"], unique=False)
    op.create_index(op.f("ix_matches_tournament_id"), "matches", ["tournament_id"], unique=False)
    op.create_index(op.f("ix_matches_winner_id"), "matches", ["winner_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_matches_winner_id"), table_name="matches")
    op.drop_index(op.f("ix_matches_tournament_id"), table_name="matches")
    op.drop_index(op.f("ix_matches_player2_id"), table_name="matches")
    op.drop_index(op.f("ix_matches_player1_id"), table_name="matches")
    op.drop_index(op.f("ix_matches_next_match_id"), table_name="matches")
    op.drop_index(op.f("ix_matches_id"), table_name="matches")
    op.drop_table("matches")
