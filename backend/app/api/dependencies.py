from __future__ import annotations

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.identity import User, UserSession
from app.services.identity import InvalidSessionError, get_valid_session

# httpOnly cookie holding the session token, so page scripts can't read it
SESSION_COOKIE = "session"


def get_current_session(
    token: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    db: Session = Depends(get_db),
) -> UserSession:
    try:
        if token is None:
            raise InvalidSessionError
        return get_valid_session(db, token=token)
    except InvalidSessionError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        ) from None


def get_current_user(
    session: UserSession = Depends(get_current_session),
) -> User:
    return session.user
