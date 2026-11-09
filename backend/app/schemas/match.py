from typing import Literal

from pydantic import BaseModel, ConfigDict


class BracketPlayerResponse(BaseModel):
    id: int | None = None
    name: str
    score: int | None = None
    status: Literal["winner", "loser", "pending"] = "pending"

    model_config = ConfigDict(from_attributes=True)


class BracketMatchResponse(BaseModel):
    id: int
    round: str
    round_number: int
    match_order: int
    players: tuple[BracketPlayerResponse, BracketPlayerResponse]
    winner_id: int | None = None
    status: str = "pending"
    next_match_id: int | None = None
    player1_reported_score: tuple[int, int] | None = None
    player2_reported_score: tuple[int, int] | None = None

    model_config = ConfigDict(from_attributes=True)


class TournamentStartResponse(BaseModel):
    message: str
    tournament_id: int
    status: str
    total_participants: int
    total_matches: int
    bracket: list[BracketMatchResponse]


class MatchScoreUpdate(BaseModel):
    score_player1: int
    score_player2: int


class MatchScoreResponse(BaseModel):
    message: str
    match: BracketMatchResponse
    tournament_status: str
    tournament_winner_id: int | None = None
    winner_id: int | None = None
    advanced_to_next_match: bool
    status: str
