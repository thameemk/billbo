from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql

from app.core.errors import NotFoundError
from app.models import Expense, Tag
from app.services import expenses as svc

NONE = dict(group_id=None, tag_id=None, q=None)


def sql(stmt):
    return str(
        stmt.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True})
    ).lower()


@pytest.fixture
def owned_group():
    with patch("app.services.expenses.get_owned_group") as m:
        yield m


@pytest.fixture
def paginate():
    with patch(
        "app.services.expenses.paginate", return_value={"items": [], "next_cursor": None}
    ) as m:
        yield m


def test_get_owned_expense(db, user):
    e = Expense()
    db.scalar.return_value = e
    eid = uuid4()
    assert svc.get_owned_expense(db, eid, user) is e
    text = sql(db.scalar.call_args.args[0])  # ownership is enforced in the query itself
    assert f"expenses.id = '{eid}'" in text and f"groups.owner_id = '{user.id}'" in text
    db.scalar.return_value = None
    with pytest.raises(NotFoundError):
        svc.get_owned_expense(db, uuid4(), user)


def test_set_tags_reuses_existing_creates_missing_keeps_order(db, user):
    food = Tag(id=uuid4(), owner_id=user.id, name="food")
    db.scalars.return_value = [food]
    e = Expense()
    svc.set_tags(db, e, ["trip", "food"], user)
    assert [t.name for t in e.tags] == ["trip", "food"]
    assert e.tags[1] is food
    assert e.tags[0].owner_id == user.id


def test_create_expense(db, user, group, owned_group):
    db.scalars.return_value = []
    e = svc.create_expense(
        db, user, group_id=group.id, tags=["a"], title="t", amount=Decimal(5), date=date(2026, 1, 1)
    )
    owned_group.assert_called_once_with(db, group.id, user)
    db.add.assert_called_once_with(e)
    db.commit.assert_called_once()
    assert (e.group_id, e.title, [t.name for t in e.tags]) == (group.id, "t", ["a"])


def test_create_expense_in_foreign_group_adds_nothing(db, user, owned_group):
    owned_group.side_effect = NotFoundError("Group not found")
    with pytest.raises(NotFoundError):
        svc.create_expense(db, user, group_id=uuid4(), tags=[], title="t")
    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_update_expense(db, user):
    db.scalars.return_value = []
    e = Expense(title="old", amount=Decimal(1))
    svc.update_expense(db, e, user, tags=["a"], title="new", amount=Decimal(2))
    assert (e.title, e.amount, [t.name for t in e.tags]) == ("new", 2, ["a"])
    assert e.updated_at is not None  # bumped explicitly so tag-only edits count
    db.commit.assert_called_once()


def test_delete_expense(db):
    e = Expense()
    svc.delete_expense(db, e)
    db.delete.assert_called_once_with(e)
    db.commit.assert_called_once()


def test_list_expenses_scopes_to_owner_and_passes_paging(db, user, paginate):
    svc.list_expenses(db, user, **NONE, with_group=False, cursor="c", limit=7)
    stmt, sort_cols, model, cursor, limit = paginate.call_args.args[1:]
    assert f"groups.owner_id = '{user.id}'" in sql(stmt)
    assert (sort_cols, model, cursor, limit) == (
        (Expense.date, Expense.created_at),
        Expense,
        "c",
        7,
    )


def test_list_expenses_filters(db, user, group, owned_group, paginate):
    def stmt_for(**kw):
        svc.list_expenses(
            db, user, **{**NONE, "with_group": False, "cursor": None, "limit": 5, **kw}
        )
        return sql(paginate.call_args.args[1])

    assert f"expenses.group_id = '{group.id}'" in stmt_for(group_id=group.id)
    owned_group.assert_called_once_with(db, group.id, user)
    assert "expense_tags" in stmt_for(tag_id=uuid4())
    text = stmt_for(q="  Coffee ")
    assert "like" in text and "coffee" in text  # trimmed, matches title or tag name
    assert "tags.name" in text
    assert "like" not in stmt_for(q="   ")


def test_list_expenses_foreign_group_404(db, user, owned_group, paginate):
    owned_group.side_effect = NotFoundError("Group not found")
    with pytest.raises(NotFoundError):
        svc.list_expenses(
            db, user, group_id=uuid4(), tag_id=None, q=None, with_group=False, cursor=None, limit=5
        )
    paginate.assert_not_called()


def test_search_escapes_wildcards(db, user, paginate):
    svc.list_expenses(db, user, **{**NONE, "q": "100%"}, with_group=False, cursor=None, limit=5)
    assert "100/%" in sql(paginate.call_args.args[1])


def test_monthly_totals_applies_range_and_returns_rows(db, user):
    db.execute.return_value.all.return_value = [("2026-02", "INR", 7, 0)]
    rows = svc.monthly_totals(db, user, **NONE, start=date(2026, 2, 1), end=date(2026, 3, 1))
    text = sql(db.execute.call_args.args[0])
    assert "expenses.date >= '2026-02-01'" in text and "expenses.date < '2026-03-01'" in text
    assert "group by" in text and rows == [("2026-02", "INR", 7, 0)]


def test_monthly_totals_unbounded(db, user):
    svc.monthly_totals(db, user, **NONE, start=None, end=None)
    assert "expenses.date >=" not in sql(db.execute.call_args.args[0])


def test_overview_runs_group_and_tag_queries(db, user):
    groups_rows, tag_rows = [("INR", 10, 4, 2, uuid4(), "Home")], [("INR", 10, 4, 1, uuid4(), "a")]
    db.execute.side_effect = [MagicMock(all=lambda: groups_rows), MagicMock(all=lambda: tag_rows)]
    assert svc.overview(db, user, date(2026, 1, 1), date(2026, 2, 1)) == (groups_rows, tag_rows)
    group_sql, tag_sql = (sql(c.args[0]) for c in db.execute.call_args_list)
    assert "expense_tags" not in group_sql and "expense_tags" in tag_sql
    assert (
        "expenses.date >= '2026-01-01'" in group_sql and "expenses.date < '2026-02-01'" in tag_sql
    )
