"""add winner to tournaments

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-09 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("tournaments", sa.Column("winner_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_tournaments_winner_id"), "tournaments", ["winner_id"], unique=False)
    op.create_foreign_key(
        op.f("fk_tournaments_winner_id_users"),
        "tournaments",
        "users",
        ["winner_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("fk_tournaments_winner_id_users"), "tournaments", type_="foreignkey")
    op.drop_index(op.f("ix_tournaments_winner_id"), table_name="tournaments")
    op.drop_column("tournaments", "winner_id")
