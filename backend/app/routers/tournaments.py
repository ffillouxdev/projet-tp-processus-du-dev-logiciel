from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.dependencies import (
    build_visible_tournaments_stmt,
    can_user_view_tournament,
    get_current_active_user,
    get_optional_current_user,
    require_association_admin,
    require_tournament_admin,
)
from app.models.match import Match
from app.models.participant import TournamentParticipant
from app.models.tournament import Tournament
from app.models.user import User
from app.schemas.match import BracketMatchResponse, BracketPlayerResponse, TournamentStartResponse
from app.schemas.tournament import (
    TournamentCreate,
    TournamentDetailResponse,
    TournamentParticipantResponse,
    TournamentResponse,
    TournamentStatus,
    TournamentUpdate,
)
from app.services.bracket import generate_single_elimination_bracket

router = APIRouter()


@router.post(
    "",
    response_model=TournamentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a tournament",
    description=(
        "Creates a new tournament for an association. "
        "Restricted to platform administrators or admins/organizers of the target association."
    ),
)
def create_tournament(
    tournament_in: TournamentCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TournamentResponse:
    association = require_association_admin(
        association_id=tournament_in.association_id,
        current_user=current_user,
        db=db,
    )

    tournament = Tournament(
        name=tournament_in.name,
        description=tournament_in.description,
        status=tournament_in.status,
        max_participants=tournament_in.max_participants,
        start_date=tournament_in.start_date,
        end_date=tournament_in.end_date,
        association_id=association.id,
    )
    db.add(tournament)
    db.commit()
    db.refresh(tournament)
    return TournamentResponse.model_validate(tournament)


@router.get(
    "",
    response_model=list[TournamentResponse],
    summary="List visible tournaments",
    description=(
        "Returns all tournaments the current user is allowed to see. "
        "Published tournaments (open, ongoing, finished) are visible to everyone; "
        "draft tournaments are only visible to members of the organizing association "
        "and platform administrators."
    ),
)
def list_tournaments(
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
    db: Annotated[Session, Depends(get_db)],
    association_id: Annotated[
        int | None, Query(description="Optional organizing association ID filter")
    ] = None,
    tournament_status: Annotated[
        TournamentStatus | None,
        Query(alias="status", description="Optional tournament status filter"),
    ] = None,
) -> list[TournamentResponse]:
    stmt = build_visible_tournaments_stmt(current_user)
    if association_id is not None:
        stmt = stmt.where(Tournament.association_id == association_id)
    if tournament_status is not None:
        stmt = stmt.where(Tournament.status == tournament_status)

    stmt = stmt.order_by(Tournament.id)
    tournaments = db.scalars(stmt).all()
    return [TournamentResponse.model_validate(t) for t in tournaments]


@router.get(
    "/{tournament_id}",
    response_model=TournamentDetailResponse,
    summary="Get a tournament by ID",
    description=(
        "Returns the details of a tournament if the user has permission to view it. "
        "Protected (draft) tournaments require membership in the organizing association "
        "or platform administrator privileges."
    ),
)
def get_tournament(
    tournament_id: int,
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TournamentDetailResponse:
    stmt = (
        select(Tournament)
        .options(
            selectinload(Tournament.association),
            selectinload(Tournament.participants).selectinload(TournamentParticipant.user),
        )
        .where(Tournament.id == tournament_id)
    )
    tournament = db.scalar(stmt)
    if tournament is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tournament not found",
        )

    if not can_user_view_tournament(db, tournament, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this tournament",
        )

    return TournamentDetailResponse.model_validate(tournament)


@router.patch(
    "/{tournament_id}",
    response_model=TournamentResponse,
    summary="Update a tournament",
    description=(
        "Updates a tournament's details or status. "
        "Restricted to platform administrators or admins/organizers of the organizing association."
    ),
)
def update_tournament(
    tournament_update: TournamentUpdate,
    tournament: Annotated[Tournament, Depends(require_tournament_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> TournamentResponse:
    if tournament_update.name is not None:
        tournament.name = tournament_update.name
    if "description" in tournament_update.model_fields_set:
        tournament.description = tournament_update.description
    if tournament_update.status is not None:
        tournament.status = tournament_update.status
    if "max_participants" in tournament_update.model_fields_set:
        tournament.max_participants = tournament_update.max_participants
    if "start_date" in tournament_update.model_fields_set:
        tournament.start_date = tournament_update.start_date
    if "end_date" in tournament_update.model_fields_set:
        tournament.end_date = tournament_update.end_date

    if (
        tournament.start_date is not None
        and tournament.end_date is not None
        and tournament.end_date < tournament.start_date
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="end_date must be greater than or equal to start_date",
        )

    db.commit()
    db.refresh(tournament)
    return TournamentResponse.model_validate(tournament)


@router.delete(
    "/{tournament_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a tournament",
    description=(
        "Deletes a tournament and its registrations. "
        "Restricted to platform administrators or admins/organizers of the organizing association."
    ),
)
def delete_tournament(
    tournament: Annotated[Tournament, Depends(require_tournament_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    db.delete(tournament)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _get_open_tournament_for_registration(
    db: Session, tournament_id: int, current_user: User
) -> Tournament:
    """Load and lock a tournament whose registrations the user may change.

    The row lock serializes concurrent registrations so max_participants cannot be exceeded.
    """
    tournament = db.scalar(
        select(Tournament).where(Tournament.id == tournament_id).with_for_update()
    )
    if tournament is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tournament not found",
        )
    if not can_user_view_tournament(db, tournament, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this tournament",
        )
    if tournament.status != "open":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tournament registrations are not open",
        )
    return tournament


@router.post(
    "/{tournament_id}/participants",
    response_model=TournamentParticipantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Join a tournament",
    description=(
        "Registers the authenticated user in the tournament reached through its public link. "
        "Registration is only possible while the tournament is open and not full."
    ),
)
def join_tournament(
    tournament_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TournamentParticipantResponse:
    tournament = _get_open_tournament_for_registration(db, tournament_id, current_user)
    if db.get(TournamentParticipant, (tournament.id, current_user.id)) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Already registered in this tournament",
        )
    if tournament.max_participants is not None:
        registered = db.scalar(
            select(func.count())
            .select_from(TournamentParticipant)
            .where(TournamentParticipant.tournament_id == tournament.id)
        )
        if (registered or 0) >= tournament.max_participants:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Tournament is full",
            )

    participant = TournamentParticipant(tournament_id=tournament.id, user_id=current_user.id)
    db.add(participant)
    db.commit()
    db.refresh(participant)
    return TournamentParticipantResponse.model_validate(participant)


@router.delete(
    "/{tournament_id}/participants/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Leave a tournament",
    description=(
        "Cancels the authenticated user's registration. "
        "Only possible while the tournament registrations are still open."
    ),
)
def leave_tournament(
    tournament_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    tournament = _get_open_tournament_for_registration(db, tournament_id, current_user)
    participant = db.get(TournamentParticipant, (tournament.id, current_user.id))
    if participant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not registered in this tournament",
        )
    db.delete(participant)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _serialize_match_to_bracket_match(match: Match) -> BracketMatchResponse:
    """Helper to convert a Match database model into a frontend-compatible BracketMatchResponse."""
    p1 = match.player1
    p2 = match.player2

    def _player_status(player: User | None) -> Literal["winner", "loser", "pending"]:
        if player is None:
            return "loser" if match.status == "completed" else "pending"
        if match.winner_id is not None:
            return "winner" if match.winner_id == player.id else "loser"
        return "pending"

    p1_resp = BracketPlayerResponse(
        id=p1.id if p1 else None,
        name=p1.full_name or p1.username if p1 else "BYE",
        score=match.score_player1,
        status=_player_status(p1),
    )
    p2_resp = BracketPlayerResponse(
        id=p2.id if p2 else None,
        name=p2.full_name or p2.username if p2 else "BYE",
        score=match.score_player2,
        status=_player_status(p2),
    )

    return BracketMatchResponse(
        id=match.id,
        round=match.round_name,
        round_number=match.round_number,
        match_order=match.match_order,
        players=(p1_resp, p2_resp),
        winner_id=match.winner_id,
        status=match.status,
        next_match_id=match.next_match_id,
    )


@router.post(
    "/{tournament_id}/start",
    response_model=TournamentStartResponse,
    summary="Start a tournament and generate its bracket",
    description=(
        "Launches the tournament: verifies participants, randomly generates the initial single "
        "elimination bracket with byes if necessary, updates status to ongoing, and returns "
        "the generated bracket. Restricted to tournament organizers and platform administrators."
    ),
)
def start_tournament(
    tournament: Annotated[Tournament, Depends(require_tournament_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> TournamentStartResponse:
    if tournament.status == "ongoing":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tournament is already ongoing",
        )
    if tournament.status == "finished":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot start a finished tournament",
        )

    # Retrieve registered participants
    stmt = (
        select(User)
        .join(TournamentParticipant, TournamentParticipant.user_id == User.id)
        .where(TournamentParticipant.tournament_id == tournament.id)
        .order_by(TournamentParticipant.registered_at)
    )
    participants = db.scalars(stmt).all()

    if len(participants) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tournament must have at least 2 participants to be started",
        )

    # Clear any previous matches if re-starting from draft
    for existing_match in tournament.matches:
        db.delete(existing_match)
    db.flush()

    # Generate the single elimination bracket
    matches = generate_single_elimination_bracket(
        db=db,
        tournament=tournament,
        participant_users=participants,
    )

    tournament.status = "ongoing"
    db.commit()

    # Refresh matches with relations for serialization
    refreshed_matches = db.scalars(
        select(Match)
        .options(selectinload(Match.player1), selectinload(Match.player2))
        .where(Match.tournament_id == tournament.id)
        .order_by(Match.round_number, Match.match_order)
    ).all()

    bracket = [_serialize_match_to_bracket_match(m) for m in refreshed_matches]

    return TournamentStartResponse(
        message="Tournament started successfully and bracket generated",
        tournament_id=tournament.id,
        status=tournament.status,
        total_participants=len(participants),
        total_matches=len(matches),
        bracket=bracket,
    )


@router.get(
    "/{tournament_id}/bracket",
    response_model=list[BracketMatchResponse],
    summary="Get tournament bracket",
    description=(
        "Returns the single elimination bracket matches for the tournament, "
        "formatted for the frontend SingleEliminationBracket component."
    ),
)
def get_tournament_bracket(
    tournament_id: int,
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[BracketMatchResponse]:
    tournament = db.get(Tournament, tournament_id)
    if tournament is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tournament not found",
        )

    if not can_user_view_tournament(db, tournament, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this tournament",
        )

    matches = db.scalars(
        select(Match)
        .options(selectinload(Match.player1), selectinload(Match.player2))
        .where(Match.tournament_id == tournament.id)
        .order_by(Match.round_number, Match.match_order)
    ).all()

    return [_serialize_match_to_bracket_match(m) for m in matches]
