import base64
import json
from datetime import date, datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.errors import InvalidCursorError
from app.models import Expense
from app.utils.pagination import paginate

SORT = (Expense.date, Expense.created_at)


def row(day):
    return SimpleNamespace(
        id=uuid4(), date=date(2026, 1, day), created_at=datetime(2026, 1, day, tzinfo=timezone.utc)
    )


def run(db, rows, cursor=None, limit=2):
    db.scalars.return_value.all.return_value = rows
    return paginate(db, select(Expense), SORT, Expense, cursor, limit)


def test_last_page_has_no_cursor(db):
    rows = [row(2), row(1)]
    assert run(db, rows) == {"items": rows, "next_cursor": None}


def test_full_page_trims_extra_row_and_encodes_last_key(db):
    rows = [row(3), row(2), row(1)]  # limit + 1 fetched
    page = run(db, rows)
    assert page["items"] == rows[:2]
    *vals, row_id = json.loads(base64.urlsafe_b64decode(page["next_cursor"]))
    assert vals == [rows[1].date.isoformat(), rows[1].created_at.isoformat()]
    assert row_id == str(rows[1].id)


def test_fetches_one_extra_row_and_applies_cursor_filter(db):
    page = run(db, [row(3), row(2), row(1)])
    run(db, [], cursor=page["next_cursor"])
    first, second = (c.args[0] for c in db.scalars.call_args_list)
    assert first.whereclause is None and second.whereclause is not None
    assert second._limit == 3


def b64(text):
    return base64.urlsafe_b64encode(text.encode()).decode()


@pytest.mark.parametrize(
    "cursor",
    [
        "!!!",
        b64("not json"),
        b64("[]"),  # nothing to unpack
        b64(json.dumps(["2026-01-01", str(uuid4())])),  # wrong number of sort values
        b64(json.dumps(["nope", "nope", str(uuid4())])),
        b64(json.dumps([1, 2, 3])),
        b64(json.dumps(["2026-01-01", "2026-01-01T00:00:00+00:00", "not-a-uuid"])),
    ],
)
def test_bad_cursor(db, cursor):
    with pytest.raises(InvalidCursorError):
        run(db, [], cursor=cursor)
