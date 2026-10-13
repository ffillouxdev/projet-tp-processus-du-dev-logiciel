from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.association import Association
    from app.models.participant import TournamentParticipant


class Tournament(Base):
    __tablename__ = "tournaments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        default="draft",
        server_default="draft",
        nullable=False,
    )
    max_participants: Mapped[int | None] = mapped_column(Integer, nullable=True)
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    association_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("associations.id", ondelete="CASCADE"),
        nullable=False,
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

    association: Mapped[Association] = relationship("Association", back_populates="tournaments")
    participants: Mapped[list[TournamentParticipant]] = relationship(
        "TournamentParticipant",
        back_populates="tournament",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
