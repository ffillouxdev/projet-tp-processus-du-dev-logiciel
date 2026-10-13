"""associations, roles, memberships, tournaments and participants

Also gives every user a global role, "participant" by default (users.role_id).

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-13 11:06:38.610747

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "associations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_associations_id"), "associations", ["id"], unique=False)
    op.create_index(op.f("ix_associations_name"), "associations", ["name"], unique=True)
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_roles_id"), "roles", ["id"], unique=False)
    op.create_index(op.f("ix_roles_name"), "roles", ["name"], unique=True)

    # Default global role of every user, required by users.role_id
    roles = sa.table("roles", sa.column("name", sa.String), sa.column("description", sa.Text))
    op.bulk_insert(
        roles, [{"name": "participant", "description": "Default role given to every user"}]
    )
    op.add_column("users", sa.Column("role_id", sa.Integer(), nullable=True))
    op.execute("UPDATE users SET role_id = (SELECT id FROM roles WHERE name = 'participant')")
    op.alter_column("users", "role_id", nullable=False)
    op.create_index(op.f("ix_users_role_id"), "users", ["role_id"], unique=False)
    op.create_foreign_key(
        "users_role_id_fkey", "users", "roles", ["role_id"], ["id"], ondelete="RESTRICT"
    )

    op.create_table(
        "memberships",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("association_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column(
            "joined_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(["association_id"], ["associations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "association_id"),
    )
    op.create_index(
        op.f("ix_memberships_association_id"), "memberships", ["association_id"], unique=False
    )
    op.create_index(op.f("ix_memberships_role_id"), "memberships", ["role_id"], unique=False)
    op.create_table(
        "tournaments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="draft", nullable=False),
        sa.Column("max_participants", sa.Integer(), nullable=True),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("association_id", sa.Integer(), nullable=False),
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
        sa.ForeignKeyConstraint(["association_id"], ["associations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_tournaments_association_id"), "tournaments", ["association_id"], unique=False
    )
    op.create_index(op.f("ix_tournaments_id"), "tournaments", ["id"], unique=False)
    op.create_index(op.f("ix_tournaments_name"), "tournaments", ["name"], unique=False)
    op.create_table(
        "tournament_participants",
        sa.Column("tournament_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "registered_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tournament_id"], ["tournaments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("tournament_id", "user_id"),
    )
    op.create_index(
        op.f("ix_tournament_participants_user_id"),
        "tournament_participants",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_tournament_participants_user_id"), table_name="tournament_participants")
    op.drop_table("tournament_participants")
    op.drop_index(op.f("ix_tournaments_name"), table_name="tournaments")
    op.drop_index(op.f("ix_tournaments_id"), table_name="tournaments")
    op.drop_index(op.f("ix_tournaments_association_id"), table_name="tournaments")
    op.drop_table("tournaments")
    op.drop_index(op.f("ix_memberships_role_id"), table_name="memberships")
    op.drop_index(op.f("ix_memberships_association_id"), table_name="memberships")
    op.drop_table("memberships")
    op.drop_constraint("users_role_id_fkey", "users", type_="foreignkey")
    op.drop_index(op.f("ix_users_role_id"), table_name="users")
    op.drop_column("users", "role_id")
    op.drop_index(op.f("ix_roles_name"), table_name="roles")
    op.drop_index(op.f("ix_roles_id"), table_name="roles")
    op.drop_table("roles")
    op.drop_index(op.f("ix_associations_name"), table_name="associations")
    op.drop_index(op.f("ix_associations_id"), table_name="associations")
    op.drop_table("associations")
