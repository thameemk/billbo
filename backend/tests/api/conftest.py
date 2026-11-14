import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.main import app


@pytest.fixture
def anon(db):
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def client(anon, user):
    app.dependency_overrides[get_current_user] = lambda: user
    return anon
