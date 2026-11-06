from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.dependencies import get_current_superuser, require_association_admin
from app.models.association import Association
from app.models.membership import Membership
from app.models.role import Role
from app.models.user import User
from app.schemas.association import (
    AssociationCreate,
    AssociationDetailResponse,
    AssociationResponse,
    AssociationUpdate,
    MembershipCreate,
    MembershipResponse,
    MembershipRoleUpdate,
)

router = APIRouter()


@router.post(
    "",
    response_model=AssociationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an association",
    description="Creates a new organizer association. Restricted to platform administrators.",
)
def create_association(
    association_in: AssociationCreate,
    _admin: Annotated[User, Depends(get_current_superuser)],
    db: Annotated[Session, Depends(get_db)],
) -> AssociationResponse:
    existing = db.scalar(select(Association).where(Association.name == association_in.name))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An association with this name already exists",
        )

    association = Association(
        name=association_in.name,
        description=association_in.description,
    )
    db.add(association)
    db.commit()
    db.refresh(association)
    return AssociationResponse.model_validate(association)


@router.get(
    "",
    response_model=list[AssociationResponse],
    summary="List associations",
    description="Returns all associations ordered by name.",
)
def list_associations(
    db: Annotated[Session, Depends(get_db)],
) -> list[AssociationResponse]:
    associations = db.scalars(select(Association).order_by(Association.name)).all()
    return [AssociationResponse.model_validate(assoc) for assoc in associations]


@router.get(
    "/{association_id}",
    response_model=AssociationDetailResponse,
    summary="Get association details and members",
    description="Returns an association along with its members and their roles (who organizes).",
)
def get_association(
    association_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> AssociationDetailResponse:
    stmt = (
        select(Association)
        .options(
            selectinload(Association.memberships).selectinload(Membership.user),
            selectinload(Association.memberships).selectinload(Membership.role),
        )
        .where(Association.id == association_id)
    )
    association = db.scalar(stmt)
    if association is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Association not found",
        )
    return AssociationDetailResponse.model_validate(association)


@router.patch(
    "/{association_id}",
    response_model=AssociationResponse,
    summary="Update an association",
    description=(
        "Updates an association's name or description. "
        "Restricted to platform administrators or association admins/organizers."
    ),
)
def update_association(
    association_update: AssociationUpdate,
    association: Annotated[Association, Depends(require_association_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> AssociationResponse:
    if association_update.name is not None and association_update.name != association.name:
        conflict = db.scalar(select(Association).where(Association.name == association_update.name))
        if conflict is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An association with this name already exists",
            )
        association.name = association_update.name

    if "description" in association_update.model_fields_set:
        association.description = association_update.description

    db.commit()
    db.refresh(association)
    return AssociationResponse.model_validate(association)


@router.delete(
    "/{association_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an association",
    description=(
        "Deletes an association and its memberships. Restricted to platform administrators."
    ),
)
def delete_association(
    association_id: int,
    _admin: Annotated[User, Depends(get_current_superuser)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    association = db.get(Association, association_id)
    if association is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Association not found",
        )

    db.delete(association)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{association_id}/members",
    response_model=list[MembershipResponse],
    summary="List members of an association",
    description=(
        "Lists every user belonging to the association with their role. "
        "Can be filtered by role name (e.g. `?role=organizer`)."
    ),
)
def list_association_members(
    association_id: int,
    db: Annotated[Session, Depends(get_db)],
    role: Annotated[str | None, Query(description="Optional role name filter")] = None,
) -> list[MembershipResponse]:
    association = db.get(Association, association_id)
    if association is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Association not found",
        )

    stmt = (
        select(Membership)
        .options(selectinload(Membership.user), selectinload(Membership.role))
        .where(Membership.association_id == association_id)
    )
    if role is not None:
        stmt = stmt.join(Role, Membership.role_id == Role.id).where(
            func.lower(Role.name) == role.strip().lower()
        )
    stmt = stmt.order_by(Membership.joined_at)

    memberships = db.scalars(stmt).all()
    return [MembershipResponse.model_validate(m) for m in memberships]


@router.post(
    "/{association_id}/members",
    response_model=MembershipResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a user to an association with a role",
    description=(
        "Associates a user with an association and assigns them a role. "
        "Restricted to platform administrators or association admins/organizers."
    ),
)
def add_association_member(
    payload: MembershipCreate,
    association: Annotated[Association, Depends(require_association_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> MembershipResponse:
    user = db.get(User, payload.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    role = db.get(Role, payload.role_id)
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )

    existing = db.get(
        Membership,
        {"user_id": user.id, "association_id": association.id},
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a member of this association",
        )

    membership = Membership(
        user_id=user.id,
        association_id=association.id,
        role_id=role.id,
    )
    db.add(membership)
    db.commit()

    created = db.scalar(
        select(Membership)
        .options(selectinload(Membership.user), selectinload(Membership.role))
        .where(
            Membership.user_id == user.id,
            Membership.association_id == association.id,
        )
    )
    return MembershipResponse.model_validate(created)


@router.patch(
    "/{association_id}/members/{user_id}",
    response_model=MembershipResponse,
    summary="Assign or update a member's role in an association",
    description=(
        "Updates the role held by an existing association member. "
        "Restricted to platform administrators or association admins/organizers."
    ),
)
def update_association_member_role(
    user_id: int,
    payload: MembershipRoleUpdate,
    association: Annotated[Association, Depends(require_association_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> MembershipResponse:
    membership = db.get(
        Membership,
        {"user_id": user_id, "association_id": association.id},
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not a member of this association",
        )

    role = db.get(Role, payload.role_id)
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )

    membership.role_id = role.id
    db.commit()

    updated = db.scalar(
        select(Membership)
        .options(selectinload(Membership.user), selectinload(Membership.role))
        .where(
            Membership.user_id == user_id,
            Membership.association_id == association.id,
        )
    )
    return MembershipResponse.model_validate(updated)


@router.delete(
    "/{association_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a user from an association",
    description=(
        "Removes a user's membership from the association. "
        "Restricted to platform administrators or association admins/organizers."
    ),
)
def remove_association_member(
    user_id: int,
    association: Annotated[Association, Depends(require_association_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    membership = db.get(
        Membership,
        {"user_id": user_id, "association_id": association.id},
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not a member of this association",
        )

    db.delete(membership)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
