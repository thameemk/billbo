from unittest.mock import patch
from uuid import uuid4

import pytest

from app.api.dependencies import get_current_session
from app.core.config import Settings
from app.main import app
from app.models import User, UserSession
from app.services.identity import (
    DuplicateEmailError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidSessionError,
)

NEW = {"email": "New@Example.com", "password": "password123", "display_name": "New"}


def account():
    return User(id=uuid4(), email="a@example.com", display_name=None, is_active=True)


@pytest.fixture
def register():
    with patch("app.api.users.register_user_service") as m:
        yield m


def test_register(anon, register):
    register.return_value = User(
        id=uuid4(), email="new@example.com", display_name="New", is_active=True
    )
    r = anon.post("/api/v1/users", json=NEW)
    assert r.status_code == 201 and r.json()["email"] == "new@example.com"
    assert "password" not in r.text
    assert register.call_args.kwargs == {
        "email": "new@example.com",
        "password": "password123",
        "display_name": "New",
    }


def test_register_disabled(anon, register):
    off = Settings(_env_file=None, database_url="x", cors_origins="", allow_signup=False)
    with patch("app.api.users.get_settings", return_value=off):
        assert anon.post("/api/v1/users", json=NEW).status_code == 403
    register.assert_not_called()


def test_register_duplicate_is_409(anon, register):
    register.side_effect = DuplicateEmailError
    assert anon.post("/api/v1/users", json=NEW).status_code == 409


def test_login_sets_httponly_strict_cookie(anon):
    with (
        patch("app.api.users.authenticate_user", return_value=account()) as auth,
        patch("app.api.users.create_session", return_value="tok"),
    ):
        r = anon.post("/api/v1/auth/login", json={"email": " A@Example.com", "password": "pw"})
    assert r.status_code == 204
    cookie = r.headers["set-cookie"].lower()
    assert "session=tok" in cookie and "httponly" in cookie and "samesite=strict" in cookie
    assert auth.call_args.kwargs == {"email": "a@example.com", "password": "pw"}


@pytest.mark.parametrize("error,status", [(InvalidCredentialsError, 401), (InactiveUserError, 403)])
def test_login_failures(anon, error, status):
    with (
        patch("app.api.users.authenticate_user", side_effect=error),
        patch("app.api.users.create_session") as create,
    ):
        r = anon.post("/api/v1/auth/login", json={"email": "a@example.com", "password": "pw"})
    assert r.status_code == status and "set-cookie" not in r.headers
    create.assert_not_called()


@pytest.fixture
def valid_session():
    with (
        patch("app.api.dependencies.get_valid_session") as get,
        patch("app.api.dependencies.extend_session") as extend,
    ):
        get.return_value = UserSession(user=account())
        extend.return_value = False
        yield get, extend


def test_me_without_cookie_401(anon, valid_session):
    assert anon.get("/api/v1/users/me").status_code == 401
    valid_session[0].assert_not_called()


def test_me_with_invalid_session_401(anon, valid_session):
    valid_session[0].side_effect = InvalidSessionError
    anon.cookies.set("session", "bad")
    assert anon.get("/api/v1/users/me").status_code == 401


def test_me_returns_user_and_only_refreshes_cookie_when_extended(anon, valid_session):
    get, extend = valid_session
    anon.cookies.set("session", "tok")
    r = anon.get("/api/v1/users/me")
    assert r.json()["email"] == "a@example.com" and "set-cookie" not in r.headers
    assert get.call_args.kwargs["token"] == "tok"
    extend.return_value = True
    assert "session=tok" in anon.get("/api/v1/users/me").headers["set-cookie"]


def test_logout_revokes_and_clears_cookie(anon):
    session = UserSession(user=account())
    app.dependency_overrides[get_current_session] = lambda: session
    with patch("app.api.users.revoke_session") as revoke:
        r = anon.post("/api/v1/auth/logout")
    assert r.status_code == 204 and "max-age=0" in r.headers["set-cookie"].lower()
    assert revoke.call_args.kwargs["session"] is session


@pytest.mark.parametrize("path", ["/api/v1/groups", "/api/v1/tags", "/api/v1/expenses"])
def test_routers_require_auth(anon, path):
    assert anon.get(path).status_code == 401
