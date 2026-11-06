from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.role import RoleResponse


class AssociationCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v


class AssociationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, v: str | None) -> str | None:
        return v.strip() if isinstance(v, str) else v


class MemberUserSummary(BaseModel):
    id: int
    username: str
    full_name: str | None

    model_config = ConfigDict(from_attributes=True)


class MembershipCreate(BaseModel):
    user_id: int = Field(..., gt=0)
    role_id: int = Field(..., gt=0)


class MembershipRoleUpdate(BaseModel):
    role_id: int = Field(..., gt=0)


class MembershipResponse(BaseModel):
    user_id: int
    association_id: int
    role_id: int
    joined_at: datetime
    user: MemberUserSummary
    role: RoleResponse

    model_config = ConfigDict(from_attributes=True)


class AssociationResponse(BaseModel):
    id: int
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AssociationDetailResponse(AssociationResponse):
    memberships: list[MembershipResponse] = Field(default_factory=list)


class UserMembershipResponse(BaseModel):
    user_id: int
    association_id: int
    role_id: int
    joined_at: datetime
    association: AssociationResponse
    role: RoleResponse

    model_config = ConfigDict(from_attributes=True)
