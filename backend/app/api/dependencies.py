from __future__ import annotations

from fastapi import Depends, HTTPException, Response, status
from fastapi.security import APIKeyCookie
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models.identity import User, UserSession
from app.services.identity import (
    InvalidSessionError,
    extend_session,
    get_valid_session,
    session_lifetime,
)

# httpOnly cookie holding the session token, so page scripts can't read it
SESSION_COOKIE = "session"

# declares cookie auth once in the docs, instead of a parameter on every route
session_cookie = APIKeyCookie(
    name=SESSION_COOKIE,
    auto_error=False,  # get_current_session answers with a 401 of its own
    description="httpOnly session cookie set by POST /auth/login",
)

# shared response docs
UNAUTHORIZED = {401: {"description": "Missing, invalid or expired session"}}
NOT_FOUND = {404: {"description": "Not found, or not owned by the caller"}}


def set_session_cookie(response: Response, token: str) -> None:
    # SameSite=Strict: never sent on cross-site requests, which is the CSRF defence
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=int(session_lifetime.total_seconds()),
        httponly=True,
        secure=get_settings().cookie_secure,
        samesite="strict",
    )


def get_current_session(
    response: Response,
    token: str | None = Depends(session_cookie),
    db: Session = Depends(get_db),
) -> UserSession:
    try:
        if token is None:
            raise InvalidSessionError
        session = get_valid_session(db, token=token)
    except InvalidSessionError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        ) from None
    if extend_session(db, session=session):
        set_session_cookie(response, token)
    return session


def get_current_user(
    session: UserSession = Depends(get_current_session),
) -> User:
    return session.user
