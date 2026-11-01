from __future__ import annotations

from fastapi import Cookie, Depends, HTTPException, Response, status
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
    token: str | None = Cookie(default=None, alias=SESSION_COOKIE),
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
