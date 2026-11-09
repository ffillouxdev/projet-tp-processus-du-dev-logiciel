from datetime import datetime
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.association import AssociationResponse, MemberUserSummary

TournamentStatus = Literal["draft", "open", "ongoing", "finished"]
PUBLIC_TOURNAMENT_STATUSES: frozenset[str] = frozenset({"open", "ongoing", "finished"})


class TournamentCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=2000)
    status: TournamentStatus = Field(default="draft")
    max_participants: int | None = Field(default=None, gt=0)
    start_date: datetime | None = Field(default=None)
    end_date: datetime | None = Field(default=None)
    association_id: int = Field(..., gt=0)

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v

    @model_validator(mode="after")
    def validate_dates(self) -> Self:
        if self.start_date is not None and self.end_date is not None:
            if self.end_date < self.start_date:
                raise ValueError("end_date must be greater than or equal to start_date")
        return self


class TournamentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=2000)
    status: TournamentStatus | None = Field(default=None)
    max_participants: int | None = Field(default=None, gt=0)
    start_date: datetime | None = Field(default=None)
    end_date: datetime | None = Field(default=None)

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, v: str | None) -> str | None:
        return v.strip() if isinstance(v, str) else v

    @model_validator(mode="after")
    def validate_dates(self) -> Self:
        if self.start_date is not None and self.end_date is not None:
            if self.end_date < self.start_date:
                raise ValueError("end_date must be greater than or equal to start_date")
        return self


class TournamentParticipantResponse(BaseModel):
    tournament_id: int
    user_id: int
    registered_at: datetime
    user: MemberUserSummary

    model_config = ConfigDict(from_attributes=True)


class TournamentResponse(BaseModel):
    id: int
    name: str
    description: str | None
    status: str
    max_participants: int | None
    start_date: datetime | None
    end_date: datetime | None
    association_id: int
    winner_id: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TournamentDetailResponse(TournamentResponse):
    association: AssociationResponse
    winner: MemberUserSummary | None = None
    participants: list[TournamentParticipantResponse] = Field(default_factory=list)
