from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from app.api.dependencies import (
    SESSION_COOKIE,
    UNAUTHORIZED,
    get_current_session,
    get_current_user,
    set_session_cookie,
)
from app.core.config import get_settings
from app.db.session import get_db
from app.models.identity import User, UserSession
from app.services.identity import (
    DuplicateEmailError,
    InactiveUserError,
    InvalidCredentialsError,
    authenticate_user,
    create_session,
    normalize_email,
    revoke_session,
)
from app.services.identity import register_user as register_user_service

router = APIRouter(prefix="/api/v1", tags=["users"])


class UserCreate(BaseModel):
    display_name: str | None = Field(default=None, max_length=100)
    email: str = Field(max_length=320)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_user_email(cls, value: str) -> str:
        return normalize_email(value)

    @field_validator("display_name")
    @classmethod
    def normalize_display_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class LoginRequest(BaseModel):
    # No min_length: password policy applies at signup, not login
    email: str = Field(max_length=320)
    password: str = Field(max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_user_email(cls, value: str) -> str:
        return normalize_email(value)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    display_name: str | None
    email: str
    is_active: bool


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        403: {"description": "Signups are disabled"},
        409: {"description": "An account with that email already exists"},
    },
)
def register_user(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    if not get_settings().allow_signup:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Signups are disabled")
    try:
        return register_user_service(
            db,
            email=payload.email,
            password=payload.password,
            display_name=payload.display_name,
        )
    except DuplicateEmailError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with that email already exists",
        ) from None


@router.post(
    "/auth/login",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {
            "description": "Signed in; the session cookie is set",
            "headers": {
                "Set-Cookie": {
                    "description": "httpOnly, SameSite=Strict session cookie",
                    "schema": {"type": "string"},
                }
            },
        },
        401: {"description": "Invalid email or password"},
        403: {"description": "User is inactive"},
    },
)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> None:
    try:
        user = authenticate_user(db, email=payload.email, password=payload.password)
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        ) from None
    except InactiveUserError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")
    set_session_cookie(response, create_session(db, user=user))


@router.get("/users/me", response_model=UserResponse, responses=UNAUTHORIZED)
def read_current_user(user: User = Depends(get_current_user)) -> User:
    return user


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT, responses=UNAUTHORIZED)
def logout(
    response: Response,
    session: UserSession = Depends(get_current_session),
    db: Session = Depends(get_db),
) -> None:
    revoke_session(db, session=session)
    response.delete_cookie(
        SESSION_COOKIE, httponly=True, secure=get_settings().cookie_secure, samesite="strict"
    )
