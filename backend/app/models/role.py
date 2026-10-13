from typing import TYPE_CHECKING

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.membership import Membership
    from app.models.user import User

# Global role given to every user; created by the migrations
DEFAULT_ROLE_NAME = "participant"


class Role(Base):
    """Role of a user: globally (users.role_id) or inside an association (memberships)."""

    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    users: Mapped[list[User]] = relationship("User", back_populates="role")
    memberships: Mapped[list[Membership]] = relationship("Membership", back_populates="role")
