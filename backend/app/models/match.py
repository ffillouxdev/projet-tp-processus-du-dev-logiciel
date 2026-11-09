from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.tournament import Tournament
    from app.models.user import User


class Match(Base):
    """A match in a tournament bracket."""

    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tournament_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tournaments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    round_name: Mapped[str] = mapped_column(String(50), nullable=False)
    match_order: Mapped[int] = mapped_column(Integer, nullable=False)

    player1_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    player2_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    winner_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    score_player1: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score_player2: Mapped[int | None] = mapped_column(Integer, nullable=True)

    player1_reported_score_p1: Mapped[int | None] = mapped_column(Integer, nullable=True)
    player1_reported_score_p2: Mapped[int | None] = mapped_column(Integer, nullable=True)
    player2_reported_score_p1: Mapped[int | None] = mapped_column(Integer, nullable=True)
    player2_reported_score_p2: Mapped[int | None] = mapped_column(Integer, nullable=True)

    status: Mapped[str] = mapped_column(
        String(30),
        default="pending",
        server_default="pending",
        nullable=False,
    )

    next_match_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("matches.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    tournament: Mapped[Tournament] = relationship("Tournament", back_populates="matches")
    player1: Mapped[User | None] = relationship("User", foreign_keys=[player1_id])
    player2: Mapped[User | None] = relationship("User", foreign_keys=[player2_id])
    winner: Mapped[User | None] = relationship("User", foreign_keys=[winner_id])
