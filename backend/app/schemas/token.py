from pydantic import BaseModel, Field

from app.schemas.user import UserResponse


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access token lifespan in seconds")


class TokenRefreshRequest(BaseModel):
    refresh_token: str = Field(..., description="Valid refresh token")


class LoginRequest(BaseModel):
    identifier: str = Field(
        ...,
        description="User email address or username",
        min_length=3,
        max_length=255,
    )
    password: str = Field(..., description="User password")


class AuthResponse(BaseModel):
    user: UserResponse
    tokens: TokenResponse


class MessageResponse(BaseModel):
    message: str
