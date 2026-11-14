from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.errors import ConflictError, NotFoundError
from app.models import Group, Tag
from app.services import groups, tags


def test_get_owned_group(db, user, other, group):
    db.get.return_value = group
    assert groups.get_owned_group(db, group.id, user) is group
    with pytest.raises(NotFoundError):  # someone else's looks the same as missing
        groups.get_owned_group(db, group.id, other)
    db.get.return_value = None
    with pytest.raises(NotFoundError):
        groups.get_owned_group(db, uuid4(), user)


def test_create_update_delete_group(db, user):
    g = groups.create_group(db, user, name="Trip", currency="USD")
    assert (g.owner_id, g.name, g.currency) == (user.id, "Trip", "USD")
    db.add.assert_called_once_with(g)
    groups.update_group(db, g, {"name": "Trip 2"})
    assert (g.name, g.currency) == ("Trip 2", "USD")
    groups.delete_group(db, g)
    db.delete.assert_called_once_with(g)
    assert db.commit.call_count == 3


def test_list_groups_merges_totals_and_defaults_empty(db, user):
    busy, empty = Group(id=uuid4()), Group(id=uuid4())
    page = {"items": [busy, empty], "next_cursor": "c"}
    db.execute.return_value = [(busy.id, Decimal(15), Decimal(3), 3)]
    with patch("app.services.groups.paginate", return_value=page):
        out = groups.list_groups(db, user, None, 10)
    assert out["next_cursor"] == "c"
    assert out["items"] == [
        (busy, {"spent": 15, "received": 3, "expense_count": 3}),
        (empty, {"spent": 0, "received": 0, "expense_count": 0}),
    ]


def test_list_groups_skips_totals_query_when_page_is_empty(db, user):
    with patch("app.services.groups.paginate", return_value={"items": [], "next_cursor": None}):
        assert groups.list_groups(db, user, None, 10)["items"] == []
    db.execute.assert_not_called()


def test_get_owned_tag(db, user, other):
    t = Tag(id=uuid4(), owner_id=user.id, name="a")
    db.get.return_value = t
    assert tags.get_owned_tag(db, t.id, user) is t
    with pytest.raises(NotFoundError):
        tags.get_owned_tag(db, t.id, other)


def test_create_tag(db, user):
    db.scalar.return_value = None
    t = tags.create_tag(db, user, "a")
    assert (t.owner_id, t.name) == (user.id, "a")
    db.add.assert_called_once_with(t)
    db.commit.assert_called_once()


def test_create_tag_name_taken(db, user):
    db.scalar.return_value = uuid4()
    with pytest.raises(ConflictError):
        tags.create_tag(db, user, "a")
    db.add.assert_not_called()


def test_rename_tag(db, user):
    t = Tag(id=uuid4(), owner_id=user.id, name="a")
    db.scalar.return_value = None
    assert tags.rename_tag(db, t, "a") is t  # unchanged name: no lookup, no commit
    db.scalar.assert_not_called()
    db.commit.assert_not_called()
    assert tags.rename_tag(db, t, "b").name == "b"
    db.commit.assert_called_once()


def test_rename_tag_name_taken(db, user):
    t = Tag(id=uuid4(), owner_id=user.id, name="a")
    db.scalar.return_value = uuid4()
    with pytest.raises(ConflictError):
        tags.rename_tag(db, t, "b")
    assert t.name == "a"


def test_commit_tags_turns_unique_race_into_conflict(db):
    db.commit.side_effect = IntegrityError("stmt", {}, Exception("violates uq_tags_owner_id_name"))
    with pytest.raises(ConflictError):
        tags.commit_tags(db)
    db.rollback.assert_called_once()


def test_commit_tags_reraises_other_integrity_errors(db):
    db.commit.side_effect = IntegrityError("stmt", {}, Exception("some other constraint"))
    with pytest.raises(IntegrityError):
        tags.commit_tags(db)
    db.rollback.assert_called_once()
