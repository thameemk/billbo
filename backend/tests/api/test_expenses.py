from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest

from app.core.errors import InvalidCursorError, NotFoundError
from app.models import Expense, Group, Tag

URL = "/api/v1/expenses"


@pytest.fixture
def svc():
    with patch("app.api.expenses.svc") as m:
        yield m


def expense(group=None):
    return Expense(
        id=uuid4(),
        group_id=uuid4(),
        title="Coffee",
        notes=None,
        amount=Decimal("12.50"),
        date=date(2026, 1, 15),
        tags=[Tag(id=uuid4(), name="food")],
        updated_at=datetime(2026, 1, 15, tzinfo=timezone.utc),
        group=group,
    )


def body(**kw):
    return {
        "group_id": str(uuid4()),
        "title": "Coffee",
        "amount": "12.50",
        "date": "2026-01-15",
        "tags": ["Food", "food"],
        **kw,
    }


def test_create_passes_cleaned_payload(client, db, user, svc):
    svc.create_expense.return_value = expense()
    payload = body()
    r = client.post(URL, json=payload)
    assert r.status_code == 201
    assert r.json()["amount"] == "12.50" and "group" not in r.json()
    assert svc.create_expense.call_args.args == (db, user)
    assert svc.create_expense.call_args.kwargs == {
        "group_id": UUID(payload["group_id"]),
        "title": "Coffee",
        "notes": None,
        "amount": Decimal("12.50"),
        "date": date(2026, 1, 15),
        "tags": ["food"],
    }


def test_create_in_missing_group_404(client, svc):
    svc.create_expense.side_effect = NotFoundError("Group not found")
    assert client.post(URL, json=body()).status_code == 404


def test_list_without_group(client, db, user, svc):
    svc.list_expenses.return_value = {"items": [expense()], "next_cursor": None}
    r = client.get(URL).json()
    assert "group" not in r["items"][0]
    assert svc.list_expenses.call_args.kwargs["with_group"] is False


def test_list_include_group_and_filters(client, svc):
    g = Group(id=uuid4(), name="Home", currency="INR")
    svc.list_expenses.return_value = {"items": [expense(g)], "next_cursor": "n"}
    tag_id = uuid4()
    r = client.get(f"{URL}?include=group&q=cof&tag_id={tag_id}&limit=5&cursor=c").json()
    assert r["items"][0]["group"]["name"] == "Home" and r["next_cursor"] == "n"
    assert svc.list_expenses.call_args.kwargs == {
        "group_id": None,
        "tag_id": tag_id,
        "q": "cof",
        "with_group": True,
        "cursor": "c",
        "limit": 5,
    }


def test_list_rejects_bad_params(client, svc):
    assert client.get(URL + "?include=bogus").status_code == 422
    assert client.get(URL + "?limit=101").status_code == 422
    svc.list_expenses.assert_not_called()


def test_bad_cursor_is_400(client, svc):
    svc.list_expenses.side_effect = InvalidCursorError("Invalid cursor")
    r = client.get(URL + "?cursor=x")
    assert r.status_code == 400 and r.json() == {"detail": "Invalid cursor"}


def test_monthly_maps_from_to_and_rows(client, svc):
    svc.monthly_totals.return_value = [("2026-01", "INR", Decimal("10"), Decimal("4"))]
    r = client.get(URL + "/monthly?from=2026-01-01&to=2026-02-01").json()
    assert r["items"][0]["month"] == "2026-01" and Decimal(r["items"][0]["received"]) == 4
    kw = svc.monthly_totals.call_args.kwargs
    assert (kw["start"], kw["end"]) == (date(2026, 1, 1), date(2026, 2, 1))


def test_overview_sorts_case_insensitively_by_name_then_currency(client, svc):
    row = lambda name, cur: (cur, Decimal(1), Decimal(0), 1, uuid4(), name)  # noqa: E731
    svc.overview.return_value = (
        [row("beta", "INR"), row("Alpha", "USD"), row("Alpha", "INR")],
        [row("x", "INR")],
    )
    r = client.get(URL + "/overview?from=2026-01-01&to=2026-02-01").json()
    assert [(g["name"], g["currency"]) for g in r["groups"]] == [
        ("Alpha", "INR"),
        ("Alpha", "USD"),
        ("beta", "INR"),
    ]
    assert r["tags"][0]["expense_count"] == 1
    assert client.get(URL + "/overview").status_code == 422


def test_update_expense(client, db, user, svc):
    e = expense()
    svc.get_owned_expense.return_value = e
    svc.update_expense.return_value = e
    assert client.put(f"{URL}/{e.id}", json=body(tags=["B"])).status_code == 200
    assert svc.update_expense.call_args.args == (db, e, user)
    assert svc.update_expense.call_args.kwargs["tags"] == ["b"]


def test_update_and_delete_missing_404(client, svc):
    svc.get_owned_expense.side_effect = NotFoundError("Expense not found")
    eid = uuid4()
    assert client.put(f"{URL}/{eid}", json=body()).status_code == 404
    assert client.delete(f"{URL}/{eid}").status_code == 404
    svc.delete_expense.assert_not_called()


def test_delete_expense(client, svc):
    e = expense()
    svc.get_owned_expense.return_value = e
    assert client.delete(f"{URL}/{e.id}").status_code == 204
    assert svc.delete_expense.call_args.args[1] is e
