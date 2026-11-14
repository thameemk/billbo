from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

import pytest

from app.core.errors import ConflictError, NotFoundError
from app.models import Group, Tag


@pytest.fixture
def groups_svc():
    with patch("app.api.groups.svc") as m:
        yield m


@pytest.fixture
def tags_svc():
    with patch("app.api.tags.svc") as m:
        yield m


def test_create_group_normalizes_input(client, db, user, groups_svc):
    groups_svc.create_group.return_value = Group(id=uuid4(), name="Trip", currency="USD")
    r = client.post("/api/v1/groups", json={"name": " Trip ", "currency": "usd"})
    assert r.status_code == 201 and r.json()["currency"] == "USD"
    groups_svc.create_group.assert_called_once_with(db, user, name="Trip", currency="USD")


def test_list_groups_shapes_totals(client, db, user, groups_svc):
    g = Group(id=uuid4(), name="Home", currency="INR")
    totals = {"spent": Decimal("10"), "received": Decimal("4"), "expense_count": 2}
    groups_svc.list_groups.return_value = {"items": [(g, totals)], "next_cursor": "c"}
    r = client.get("/api/v1/groups?limit=5&cursor=abc").json()
    assert r["next_cursor"] == "c"
    assert (r["items"][0]["name"], r["items"][0]["expense_count"]) == ("Home", 2)
    assert Decimal(r["items"][0]["spent"]) == 10
    groups_svc.list_groups.assert_called_once_with(db, user, "abc", 5)
    assert client.get("/api/v1/groups?limit=0").status_code == 422


def test_update_group_sends_only_given_fields(client, groups_svc):
    g = Group(id=uuid4(), name="Old", currency="INR")
    groups_svc.get_owned_group.return_value = g
    groups_svc.update_group.return_value = g
    assert client.patch(f"/api/v1/groups/{g.id}", json={"name": "New"}).status_code == 200
    assert groups_svc.update_group.call_args.args[1:] == (g, {"name": "New"})


def test_group_not_found_is_404(client, groups_svc):
    groups_svc.get_owned_group.side_effect = NotFoundError("Group not found")
    gid = uuid4()
    for r in (
        client.patch(f"/api/v1/groups/{gid}", json={"name": "n"}),
        client.delete(f"/api/v1/groups/{gid}"),
    ):
        assert r.status_code == 404 and r.json() == {"detail": "Group not found"}
    groups_svc.delete_group.assert_not_called()


def test_delete_group(client, groups_svc):
    g = Group(id=uuid4())
    groups_svc.get_owned_group.return_value = g
    assert client.delete(f"/api/v1/groups/{g.id}").status_code == 204
    assert groups_svc.delete_group.call_args.args[1] is g


def test_list_tags(client, tags_svc):
    tags_svc.list_tags.return_value = [Tag(id=uuid4(), name="a")]
    assert [t["name"] for t in client.get("/api/v1/tags").json()["items"]] == ["a"]


def test_create_tag_lowercases_and_maps_conflict(client, db, user, tags_svc):
    tags_svc.create_tag.return_value = Tag(id=uuid4(), name="food")
    assert client.post("/api/v1/tags", json={"name": " Food "}).status_code == 201
    tags_svc.create_tag.assert_called_once_with(db, user, "food")
    tags_svc.create_tag.side_effect = ConflictError("Tag already exists")
    r = client.post("/api/v1/tags", json={"name": "food"})
    assert r.status_code == 409 and r.json() == {"detail": "Tag already exists"}


def test_rename_and_delete_tag(client, tags_svc):
    t = Tag(id=uuid4(), name="a")
    tags_svc.get_owned_tag.return_value = t
    tags_svc.rename_tag.return_value = Tag(id=t.id, name="b")
    assert client.patch(f"/api/v1/tags/{t.id}", json={"name": "B"}).json()["name"] == "b"
    assert tags_svc.rename_tag.call_args.args[1:] == (t, "b")
    assert client.delete(f"/api/v1/tags/{t.id}").status_code == 204
    tags_svc.get_owned_tag.side_effect = NotFoundError("Tag not found")
    assert client.delete(f"/api/v1/tags/{t.id}").status_code == 404
