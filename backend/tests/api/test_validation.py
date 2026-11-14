"""Request-model rules; no database needed."""

import pytest
from pydantic import ValidationError

from app.api.expenses import ExpenseUpdate
from app.api.groups import GroupCreate, GroupUpdate
from app.api.tags import TagBody
from app.api.users import UserCreate

BASE = {"title": "t", "amount": "1.00", "date": "2026-01-01"}


def test_expense_tags_cleaned():
    e = ExpenseUpdate(**BASE, tags=[" Food ", "food", "", "Trip"])
    assert e.tags == ["food", "trip"]


@pytest.mark.parametrize(
    "override",
    [
        {"amount": 12.5},  # number, not string
        {"amount": "0"},
        {"amount": "0.00"},
        {"amount": "1.234"},  # too many decimals
        {"amount": "1234567890123"},  # too many digits
        {"title": "   "},
        {"tags": [f"t{i}" for i in range(11)]},
        {"tags": ["a" * 31]},
        {"date": "nope"},
    ],
)
def test_expense_rejects(override):
    with pytest.raises(ValidationError):
        ExpenseUpdate(**{**BASE, **override})


def test_expense_accepts_credit():
    assert ExpenseUpdate(**{**BASE, "amount": "-5"}).amount == -5


def test_group_currency():
    assert GroupCreate(name=" Trip ", currency="usd").currency == "USD"
    assert GroupCreate(name="x").currency == "INR"
    for bad in ("XXX1", "ZZZ", "us"):
        with pytest.raises(ValidationError):
            GroupCreate(name="x", currency=bad)
    assert GroupUpdate().currency is None
    with pytest.raises(ValidationError):
        GroupUpdate(currency="ZZZ")


def test_tag_body_lowercases_and_strips():
    assert TagBody(name="  Food ").name == "food"
    with pytest.raises(ValidationError):
        TagBody(name="  ")


def test_user_create_normalizes():
    u = UserCreate(email=" A@X.com ", password="12345678", display_name="  ")
    assert (u.email, u.display_name) == ("a@x.com", None)
    with pytest.raises(ValidationError):
        UserCreate(email="a@x.com", password="short")
    with pytest.raises(ValidationError):
        UserCreate(email="bad", password="12345678")
