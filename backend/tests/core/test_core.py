import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.errors import (
    ConflictError,
    InvalidCursorError,
    NotFoundError,
    register_error_handlers,
)


def test_cors_origin_list_splits_and_drops_blanks():
    s = Settings(database_url="x", cors_origins=" http://a.com, ,http://b.com ,")
    assert s.cors_origin_list == ["http://a.com", "http://b.com"]


def test_settings_defaults(monkeypatch):
    monkeypatch.delenv("ALLOW_SIGNUP", raising=False)
    monkeypatch.delenv("COOKIE_SECURE", raising=False)
    s = Settings(_env_file=None, database_url="x", cors_origins="")
    assert s.allow_signup is False
    assert s.cookie_secure is True
    assert s.cors_origin_list == []


@pytest.mark.parametrize(
    "exc,status",
    [(InvalidCursorError, 400), (NotFoundError, 404), (ConflictError, 409)],
)
def test_error_handlers_map_status(exc, status):
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/boom")
    def boom():
        raise exc("nope")

    r = TestClient(app).get("/boom")
    assert r.status_code == status
    assert r.json() == {"detail": "nope"}
