import uuid
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_active_user
from app.models.token import RefreshToken
from app.models.user import User
from app.schemas.token import (
    AuthResponse,
    LoginRequest,
    MessageResponse,
    TokenRefreshRequest,
    TokenResponse,
)
from app.schemas.user import (
    ChangePasswordRequest,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from app.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)

router = APIRouter()


def _issue_tokens_for_user(user: User, db: Session) -> TokenResponse:
    """Helper to generate an access/refresh token pair and persist the refresh token."""
    token_jti = uuid.uuid4().hex
    access_token = create_access_token(user_id=user.id)
    refresh_token, expires_at = create_refresh_token(user_id=user.id, token_jti=token_jti)

    db_token = RefreshToken(
        token_jti=token_jti,
        user_id=user.id,
        expires_at=expires_at,
        revoked=False,
    )
    db.add(db_token)
    db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Creates a new user account, hashes password with Argon2, and returns auth tokens.",
)
def register(
    user_in: UserCreate,
    db: Annotated[Session, Depends(get_db)],
) -> AuthResponse:
    # Check if email is already registered
    existing_email = db.scalar(select(User).where(User.email == user_in.email))
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    # Check if username is already taken
    existing_username = db.scalar(select(User).where(User.username == user_in.username))
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this username already exists",
        )

    # Hash password and create user
    user = User(
        email=user_in.email,
        username=user_in.username,
        full_name=user_in.full_name,
        hashed_password=get_password_hash(user_in.password),
        is_active=True,
        is_superuser=False,
    )
    db.add(user)
    db.flush()  # Generate user.id

    tokens = _issue_tokens_for_user(user, db)
    return AuthResponse(user=UserResponse.model_validate(user), tokens=tokens)


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="User login with email/username and password",
    description="Authenticates credentials and returns a fresh access token and refresh token.",
)
def login(
    credentials: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
) -> AuthResponse:
    # Support login with either email or username
    user = db.scalar(
        select(User).where(
            (User.email == credentials.identifier) | (User.username == credentials.identifier)
        )
    )

    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    tokens = _issue_tokens_for_user(user, db)
    return AuthResponse(user=UserResponse.model_validate(user), tokens=tokens)


@router.post(
    "/token",
    response_model=TokenResponse,
    summary="OAuth2 standard token endpoint",
    description="Complies with the OAuth2 spec for Swagger UI authorization and standard clients.",
)
def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    user = db.scalar(
        select(User).where(
            (User.email == form_data.username) | (User.username == form_data.username)
        )
    )

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return _issue_tokens_for_user(user, db)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    description=(
        "Uses a valid refresh token to issue a new access token and a new rotated refresh token. "
        "The previous refresh token is revoked to prevent replay attacks."
    ),
)
def refresh_token(
    payload: TokenRefreshRequest,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    try:
        token_data = decode_token(payload.refresh_token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    if token_data.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type: refresh token required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    jti = token_data.get("jti")
    user_id_str = token_data.get("sub")
    if not jti or not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = int(user_id_str)
    except ValueError, TypeError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user identifier",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    # Check token record in DB
    db_token = db.scalar(select(RefreshToken).where(RefreshToken.token_jti == jti))
    if not db_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not recognized",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if db_token.revoked:
        # Replay attack suspected: invalidate all refresh tokens for this user for safety
        revocation_list = db.scalars(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id, RefreshToken.revoked.is_(False)
            )
        ).all()
        for token in revocation_list:
            token.revoked = True
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked. All sessions invalidated for security.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer active or exists",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Rotate refresh token: revoke current one and issue a fresh pair
    db_token.revoked = True
    new_tokens = _issue_tokens_for_user(user, db)
    return new_tokens


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
    description="Returns the profile details of the currently authenticated user.",
)
def get_current_user_profile(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update current user profile",
    description="Allows updating email, username, or full_name.",
)
def update_current_user_profile(
    user_update: UserUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> UserResponse:
    if user_update.email is not None and user_update.email != current_user.email:
        existing = db.scalar(select(User).where(User.email == user_update.email))
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email already exists",
            )
        current_user.email = user_update.email

    if user_update.username is not None and user_update.username != current_user.username:
        existing = db.scalar(select(User).where(User.username == user_update.username))
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this username already exists",
            )
        current_user.username = user_update.username

    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name

    db.commit()
    db.refresh(current_user)
    return UserResponse.model_validate(current_user)


@router.post(
    "/change-password",
    response_model=MessageResponse,
    summary="Change user password",
    description=(
        "Verifies the current password, updates to a new password, "
        "and revokes all active refresh tokens."
    ),
)
def change_password(
    payload: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    current_user.hashed_password = get_password_hash(payload.new_password)

    # Invalidate all active refresh tokens on password change
    tokens = db.scalars(
        select(RefreshToken).where(
            RefreshToken.user_id == current_user.id,
            RefreshToken.revoked.is_(False),
        )
    ).all()
    for token in tokens:
        token.revoked = True

    db.commit()
    return MessageResponse(
        message="Password updated successfully. All active sessions have been revoked."
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout user",
    description="Revokes the provided refresh token so it cannot be used anymore.",
)
def logout(
    payload: TokenRefreshRequest,
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    try:
        token_data = decode_token(payload.refresh_token)
        jti = token_data.get("jti")
        if jti:
            db_token = db.scalar(select(RefreshToken).where(RefreshToken.token_jti == jti))
            if db_token and not db_token.revoked:
                db_token.revoked = True
                db.commit()
    except Exception:
        # Logout is idempotent: even if token was invalid or expired, return success
        pass

    return MessageResponse(message="Successfully logged out")


@router.post(
    "/logout-all",
    response_model=MessageResponse,
    summary="Logout from all devices",
    description="Revokes all refresh tokens belonging to the currently authenticated user.",
)
def logout_all(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    tokens = db.scalars(
        select(RefreshToken).where(
            RefreshToken.user_id == current_user.id,
            RefreshToken.revoked.is_(False),
        )
    ).all()
    for token in tokens:
        token.revoked = True

    db.commit()
    return MessageResponse(message="Successfully logged out from all devices")
