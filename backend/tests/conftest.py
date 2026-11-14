"""Unit tests: the DB session is a mock, nothing here touches Postgres."""

# ruff: noqa: E402  (env must be set before app imports)
import os

os.environ.update(
    DATABASE_URL="postgresql+psycopg://x/x_test",
    CORS_ORIGINS="http://localhost",
    ALLOW_SIGNUP="true",
    COOKIE_SECURE="false",
)

from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.models import Group, User


@pytest.fixture
def db():
    return MagicMock(spec=Session)


@pytest.fixture
def user():
    return User(id=uuid4(), email="a@example.com", password_hash="x", is_active=True)


@pytest.fixture
def other():
    return User(id=uuid4(), email="b@example.com", password_hash="x", is_active=True)


@pytest.fixture
def group(user):
    return Group(id=uuid4(), owner_id=user.id, name="Home", currency="INR")
