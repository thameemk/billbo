from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from pwdlib import PasswordHash
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.identity import User, UserSession

password_hash = PasswordHash.recommended()
_dummy_hash = password_hash.hash("timing-equalizer")
session_lifetime = timedelta(minutes=30)


class DuplicateEmailError(Exception):
    """Raised when an account already exists for an email address."""


class InvalidCredentialsError(Exception):
    """Raised when a login attempt cannot be authenticated."""


class InactiveUserError(Exception):
    """Raised when an inactive account attempts to log in."""


class InvalidSessionError(Exception):
    """Raised when a session is missing, expired, revoked, or inactive."""


def normalize_email(value: str) -> str:
    email = value.strip().casefold()
    if not email or "@" not in email or email.startswith("@") or email.endswith("@"):
        raise ValueError("Enter a valid email address")
    return email


def register_user(
    db: Session,
    *,
    email: str,
    password: str,
    display_name: str | None = None,
) -> User:
    user = User(
        email=normalize_email(email),
        password_hash=password_hash.hash(password),
        display_name=display_name,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise DuplicateEmailError from None
    db.refresh(user)
    return user


def authenticate_user(db: Session, *, email: str, password: str) -> User:
    user = db.scalar(select(User).where(func.lower(User.email) == normalize_email(email)))
    if user is None:
        # same argon2 cost as a real check, so response time doesn't reveal unknown emails
        password_hash.verify(password, _dummy_hash)
        raise InvalidCredentialsError
    if not password_hash.verify(password, user.password_hash):
        raise InvalidCredentialsError
    if not user.is_active:
        raise InactiveUserError
    return user


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(db: Session, *, user: User) -> str:
    token = secrets.token_urlsafe(32)
    # purges every user's expired sessions on login,
    # move to a scheduled job if login latency suffers
    db.execute(delete(UserSession).where(UserSession.expires_at <= datetime.now(timezone.utc)))
    db.add(
        UserSession(
            user_id=user.id,
            token_hash=hash_session_token(token),
            expires_at=datetime.now(timezone.utc) + session_lifetime,
        )
    )
    db.commit()
    return token


def get_valid_session(db: Session, *, token: str) -> UserSession:
    session = db.scalar(
        select(UserSession).where(
            UserSession.token_hash == hash_session_token(token),
            UserSession.expires_at > datetime.now(timezone.utc),
        )
    )
    if session is None or not session.user.is_active:
        raise InvalidSessionError
    return session


def revoke_session(db: Session, *, session: UserSession) -> None:
    db.delete(session)
    db.commit()
