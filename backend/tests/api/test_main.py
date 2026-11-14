from fastapi.testclient import TestClient

from app.main import app


def test_openapi_builds():
    assert TestClient(app).get("/openapi.json").status_code == 200
