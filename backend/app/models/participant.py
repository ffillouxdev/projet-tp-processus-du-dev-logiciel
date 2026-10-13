from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.tournament import Tournament
    from app.models.user import User


class TournamentParticipant(Base):
    """Registration of a user to a tournament."""

    __tablename__ = "tournament_participants"

    tournament_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tournaments.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    tournament: Mapped[Tournament] = relationship("Tournament", back_populates="participants")
    user: Mapped[User] = relationship("User", back_populates="participations")
