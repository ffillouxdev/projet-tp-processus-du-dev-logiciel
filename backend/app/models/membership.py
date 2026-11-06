from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.association import Association
    from app.models.role import Role
    from app.models.user import User


class Membership(Base):
    """A user belongs to an association with exactly one role in it."""

    __tablename__ = "memberships"

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    association_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("associations.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    # RESTRICT: a role cannot be deleted while it is still assigned
    role_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("roles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user: Mapped[User] = relationship("User", back_populates="memberships")
    association: Mapped[Association] = relationship("Association", back_populates="memberships")
    role: Mapped[Role] = relationship("Role", back_populates="memberships")
