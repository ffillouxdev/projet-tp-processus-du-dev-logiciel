from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_superuser
from app.models.membership import Membership
from app.models.role import Role
from app.models.user import User
from app.schemas.role import RoleCreate, RoleResponse, RoleUpdate

router = APIRouter()


@router.post(
    "",
    response_model=RoleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a role",
    description="Creates a new association role. Restricted to platform administrators.",
)
def create_role(
    role_in: RoleCreate,
    _admin: Annotated[User, Depends(get_current_superuser)],
    db: Annotated[Session, Depends(get_db)],
) -> RoleResponse:
    existing = db.scalar(select(Role).where(Role.name == role_in.name))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A role with this name already exists",
        )

    role = Role(name=role_in.name, description=role_in.description)
    db.add(role)
    db.commit()
    db.refresh(role)
    return RoleResponse.model_validate(role)


@router.get(
    "",
    response_model=list[RoleResponse],
    summary="List all roles",
    description="Returns every available association role ordered by name.",
)
def list_roles(
    db: Annotated[Session, Depends(get_db)],
) -> list[RoleResponse]:
    roles = db.scalars(select(Role).order_by(Role.name)).all()
    return [RoleResponse.model_validate(role) for role in roles]


@router.get(
    "/{role_id}",
    response_model=RoleResponse,
    summary="Get a role by ID",
)
def get_role(
    role_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> RoleResponse:
    role = db.get(Role, role_id)
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )
    return RoleResponse.model_validate(role)


@router.patch(
    "/{role_id}",
    response_model=RoleResponse,
    summary="Update a role",
    description="Updates a role's name or description. Restricted to platform administrators.",
)
def update_role(
    role_id: int,
    role_update: RoleUpdate,
    _admin: Annotated[User, Depends(get_current_superuser)],
    db: Annotated[Session, Depends(get_db)],
) -> RoleResponse:
    role = db.get(Role, role_id)
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )

    if role_update.name is not None and role_update.name != role.name:
        conflict = db.scalar(select(Role).where(Role.name == role_update.name))
        if conflict is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A role with this name already exists",
            )
        role.name = role_update.name

    if "description" in role_update.model_fields_set:
        role.description = role_update.description

    db.commit()
    db.refresh(role)
    return RoleResponse.model_validate(role)


@router.delete(
    "/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a role",
    description=(
        "Deletes a role if it is not currently assigned to any membership. "
        "Restricted to platform administrators."
    ),
)
def delete_role(
    role_id: int,
    _admin: Annotated[User, Depends(get_current_superuser)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    role = db.get(Role, role_id)
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )

    in_use = db.scalar(select(Membership.role_id).where(Membership.role_id == role_id).limit(1))
    if in_use is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete role while it is assigned to members",
        )

    db.delete(role)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
