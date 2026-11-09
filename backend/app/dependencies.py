from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.association import Association
from app.models.membership import Membership
from app.models.role import Role
from app.models.tournament import Tournament
from app.models.user import User
from app.schemas.tournament import PUBLIC_TOURNAMENT_STATUSES
from app.security import decode_token, oauth2_scheme

# Roles inside an association that grant administrative rights over that association
ASSOCIATION_ADMIN_ROLES: frozenset[str] = frozenset({"admin", "organizer"})


def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Dependency that verifies the JWT access token and returns the corresponding User."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise credentials_exception

    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except jwt.PyJWTError:
        raise credentials_exception from None

    token_type = payload.get("type")
    if token_type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type: access token required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str = payload.get("sub")
    if user_id_str is None:
        raise credentials_exception

    try:
        user_id = int(user_id_str)
    except ValueError, TypeError:
        raise credentials_exception from None

    user = db.get(User, user_id)
    if user is None:
        raise credentials_exception

    return user


def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Dependency ensuring the authenticated user account is active."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )
    return current_user


def get_optional_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User | None:
    """Return the authenticated active User when a Bearer token is supplied, or None otherwise."""
    if not token:
        return None
    user = get_current_user(token=token, db=db)
    return get_current_active_user(current_user=user)


def get_current_superuser(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    """Dependency ensuring the authenticated user is a platform administrator (is_superuser)."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required",
        )
    return current_user


def require_association_admin(
    association_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Association:
    """Require platform superuser or an admin/organizer role in the target association."""
    if current_user.is_superuser:
        association = db.get(Association, association_id)
        if association is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Association not found",
            )
        return association

    stmt = (
        select(Membership)
        .join(Role, Membership.role_id == Role.id)
        .where(
            Membership.user_id == current_user.id,
            Membership.association_id == association_id,
            func.lower(Role.name).in_(ASSOCIATION_ADMIN_ROLES),
        )
    )
    membership = db.scalar(stmt)
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator or association organizer privileges required",
        )

    return membership.association


def build_visible_tournaments_stmt(current_user: User | None) -> Select[Tournament]:
    """Build a SELECT statement for tournaments visible to ``current_user``.

    - Published tournaments (status in PUBLIC_TOURNAMENT_STATUSES, i.e. not ``draft``)
      are visible to everyone.
    - Draft tournaments (``status == 'draft'``) are restricted to platform administrators
      (``is_superuser``) and members of the organizing association.
    """
    stmt = select(Tournament)
    if current_user is not None and current_user.is_superuser:
        return stmt

    public_clause = Tournament.status.in_(PUBLIC_TOURNAMENT_STATUSES)
    if current_user is None:
        return stmt.where(public_clause)

    member_association_ids = select(Membership.association_id).where(
        Membership.user_id == current_user.id
    )
    return stmt.where(
        or_(
            public_clause,
            Tournament.association_id.in_(member_association_ids),
        )
    )


def can_user_view_tournament(
    db: Session,
    tournament: Tournament,
    current_user: User | None,
) -> bool:
    """Check whether ``current_user`` is allowed to view ``tournament``."""
    if tournament.status in PUBLIC_TOURNAMENT_STATUSES:
        return True
    if current_user is None:
        return False
    if current_user.is_superuser:
        return True
    membership = db.get(
        Membership,
        {"user_id": current_user.id, "association_id": tournament.association_id},
    )
    return membership is not None


def require_tournament_admin(
    tournament_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Tournament:
    """Require platform superuser or an admin/organizer role in the tournament's association."""
    tournament = db.get(Tournament, tournament_id)
    if tournament is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tournament not found",
        )
    if current_user.is_superuser:
        return tournament

    stmt = (
        select(Membership)
        .join(Role, Membership.role_id == Role.id)
        .where(
            Membership.user_id == current_user.id,
            Membership.association_id == tournament.association_id,
            func.lower(Role.name).in_(ASSOCIATION_ADMIN_ROLES),
        )
    )
    membership = db.scalar(stmt)
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator or association organizer privileges required",
        )
    return tournament
