from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models import Expense, Group, User
from app.services.totals import received, spent
from app.utils.pagination import paginate


def get_owned_group(db: Session, group_id: UUID, user: User) -> Group:
    group = db.get(Group, group_id)
    if group is None or group.owner_id != user.id:
        raise NotFoundError("Group not found")
    return group


def create_group(db: Session, user: User, *, name: str, currency: str) -> Group:
    group = Group(owner_id=user.id, name=name, currency=currency)
    db.add(group)
    db.commit()
    return group


def update_group(db: Session, group: Group, changes: dict) -> Group:
    for field, value in changes.items():
        setattr(group, field, value)
    db.commit()
    return group


def delete_group(db: Session, group: Group) -> None:
    db.delete(group)  # its expenses go with it
    db.commit()


def list_groups(db: Session, user: User, cursor: str | None, limit: int) -> dict:
    """A page of the user's groups; each item is (group, {spent, received, expense_count})."""
    page = paginate(
        db,
        select(Group).where(Group.owner_id == user.id),
        (Group.created_at,),
        Group,
        cursor,
        limit,
    )
    ids = [g.id for g in page["items"]]
    rows = (
        db.execute(
            select(Expense.group_id, spent(), received(), func.count())
            .where(Expense.group_id.in_(ids))
            .group_by(Expense.group_id)
        )
        if ids
        else []
    )
    totals = {
        gid: {"spent": debit, "received": credit, "expense_count": count}
        for gid, debit, credit, count in rows
    }
    none = {"spent": Decimal(0), "received": Decimal(0), "expense_count": 0}
    page["items"] = [(g, totals.get(g.id, none)) for g in page["items"]]
    return page
