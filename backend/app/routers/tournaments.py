from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
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
from app.models.participant import TournamentParticipant
from app.models.tournament import Tournament
from app.models.user import User
from app.schemas.tournament import (
    TournamentCreate,
    TournamentDetailResponse,
    TournamentResponse,
    TournamentStatus,
    TournamentUpdate,
)

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
