from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import User, UserSession
from app.services import identity as ident

HASH = ident.password_hash.hash("pw")


def stored(active=True):
    return User(id=uuid4(), email="a@x.com", password_hash=HASH, is_active=active)


def test_normalize_email():
    assert ident.normalize_email("  Foo@Example.COM ") == "foo@example.com"


@pytest.mark.parametrize("bad", ["", "  ", "nope", "@x.com", "x@"])
def test_normalize_email_rejects(bad):
    with pytest.raises(ValueError):
        ident.normalize_email(bad)


def test_register_hashes_and_normalizes(db):
    u = ident.register_user(db, email=" Foo@X.com ", password="pw", display_name="Foo")
    db.add.assert_called_once_with(u)
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(u)
    assert u.email == "foo@x.com"
    assert u.password_hash != "pw" and ident.password_hash.verify("pw", u.password_hash)


def test_register_duplicate_email(db):
    db.commit.side_effect = IntegrityError("stmt", {}, Exception("dup"))
    with pytest.raises(ident.DuplicateEmailError):
        ident.register_user(db, email="a@x.com", password="pw")
    db.rollback.assert_called_once()


def test_authenticate_ok(db):
    u = stored()
    db.scalar.return_value = u
    assert ident.authenticate_user(db, email="A@x.com", password="pw") is u


def test_authenticate_wrong_password(db):
    db.scalar.return_value = stored()
    with pytest.raises(ident.InvalidCredentialsError):
        ident.authenticate_user(db, email="a@x.com", password="wrong")


def test_authenticate_unknown_email_still_pays_for_a_hash_check(db, monkeypatch):
    db.scalar.return_value = None
    spy = MagicMock()
    monkeypatch.setattr(ident, "password_hash", spy)
    with pytest.raises(ident.InvalidCredentialsError):
        ident.authenticate_user(db, email="no@x.com", password="pw")
    spy.verify.assert_called_once()  # equalises timing with a real lookup


def test_authenticate_inactive_only_after_password_is_proven(db):
    db.scalar.return_value = stored(active=False)
    with pytest.raises(ident.InactiveUserError):
        ident.authenticate_user(db, email="a@x.com", password="pw")
    with pytest.raises(ident.InvalidCredentialsError):  # don't reveal the account state
        ident.authenticate_user(db, email="a@x.com", password="wrong")


def test_create_session_stores_only_the_hash(db, user):
    before = datetime.now(timezone.utc)
    token = ident.create_session(db, user=user)
    (row,) = db.add.call_args.args
    assert row.user_id == user.id
    assert row.token_hash == ident.hash_session_token(token) != token
    assert (
        before + ident.session_lifetime
        <= row.expires_at
        <= (datetime.now(timezone.utc) + ident.session_lifetime)
    )
    db.execute.assert_called_once()  # expired sessions purged
    db.commit.assert_called_once()


def test_get_valid_session(db):
    session = UserSession(user=stored())
    db.scalar.return_value = session
    assert ident.get_valid_session(db, token="t") is session


def test_get_valid_session_missing_or_expired(db):
    db.scalar.return_value = None  # the query filters on hash and expiry
    with pytest.raises(ident.InvalidSessionError):
        ident.get_valid_session(db, token="t")


def test_get_valid_session_inactive_user(db):
    db.scalar.return_value = UserSession(user=stored(active=False))
    with pytest.raises(ident.InvalidSessionError):
        ident.get_valid_session(db, token="t")


def test_extend_session_only_past_half_life(db):
    fresh = UserSession(expires_at=datetime.now(timezone.utc) + ident.session_lifetime)
    assert ident.extend_session(db, session=fresh) is False
    db.commit.assert_not_called()

    old = UserSession(expires_at=datetime.now(timezone.utc) + timedelta(minutes=5))
    assert ident.extend_session(db, session=old) is True
    assert old.expires_at - datetime.now(timezone.utc) > timedelta(minutes=25)
    db.commit.assert_called_once()


def test_revoke_session(db):
    s = UserSession()
    ident.revoke_session(db, session=s)
    db.delete.assert_called_once_with(s)
    db.commit.assert_called_once()
