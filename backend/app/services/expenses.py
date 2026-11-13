from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, contains_eager

from app.core.errors import NotFoundError
from app.models import Expense, Group, Tag, User
from app.models.expenses import expense_tags
from app.services.groups import get_owned_group
from app.services.tags import commit_tags
from app.services.totals import received, spent
from app.utils.pagination import paginate


def get_owned_expense(db: Session, expense_id: UUID, user: User) -> Expense:
    expense = db.scalar(
        select(Expense)
        .join(Expense.group)
        .where(Expense.id == expense_id, Group.owner_id == user.id)
    )
    if expense is None:
        raise NotFoundError("Expense not found")
    return expense


def set_tags(db: Session, expense: Expense, names: list[str], user: User) -> None:
    """Point the expense at the caller's tags with these names, creating the missing ones."""
    found = {
        t.name: t
        for t in db.scalars(select(Tag).where(Tag.owner_id == user.id, Tag.name.in_(names)))
    }
    expense.tags = [found.get(n) or Tag(owner_id=user.id, name=n) for n in names]


def create_expense(
    db: Session, user: User, *, group_id: UUID, tags: list[str], **fields
) -> Expense:
    get_owned_group(db, group_id, user)  # 404 unless it is the caller's group
    expense = Expense(group_id=group_id, **fields)
    set_tags(db, expense, tags, user)
    db.add(expense)
    commit_tags(db)
    return expense


def update_expense(
    db: Session, expense: Expense, user: User, *, tags: list[str], **fields
) -> Expense:
    for field, value in fields.items():
        setattr(expense, field, value)
    set_tags(db, expense, tags, user)
    expense.updated_at = func.now()  # onupdate alone misses tag-only edits
    commit_tags(db)
    return expense


def delete_expense(db: Session, expense: Expense) -> None:
    db.delete(expense)
    db.commit()


def _filtered(db: Session, stmt, user: User, group_id: UUID | None, tag_id: UUID | None, q):
    if group_id:
        get_owned_group(db, group_id, user)  # 404 unless it is the caller's group
    stmt = stmt.join(Expense.group).where(Group.owner_id == user.id)
    if group_id:
        stmt = stmt.where(Expense.group_id == group_id)
    if tag_id:
        stmt = stmt.where(Expense.tags.any(Tag.id == tag_id))
    if q and q.strip():
        q = q.strip()
        stmt = stmt.where(
            Expense.title.icontains(q, autoescape=True)
            | Expense.tags.any(Tag.name.icontains(q, autoescape=True))
        )
    return stmt


def list_expenses(
    db: Session,
    user: User,
    *,
    group_id: UUID | None,
    tag_id: UUID | None,
    q: str | None,
    with_group: bool,
    cursor: str | None,
    limit: int,
) -> dict:
    stmt = _filtered(db, select(Expense), user, group_id, tag_id, q)
    if with_group:
        stmt = stmt.options(contains_eager(Expense.group))
    return paginate(db, stmt, (Expense.date, Expense.created_at), Expense, cursor, limit)


def monthly_totals(
    db: Session,
    user: User,
    *,
    group_id: UUID | None,
    tag_id: UUID | None,
    q: str | None,
    start: date | None,
    end: date | None,
):
    """Rows of (month, currency, spent, received) over everything matched within [start, end)."""
    month = func.to_char(Expense.date, "YYYY-MM")
    stmt = _filtered(
        db, select(month, Group.currency, spent(), received()), user, group_id, tag_id, q
    ).group_by(month, Group.currency)
    if start:
        stmt = stmt.where(Expense.date >= start)
    if end:
        stmt = stmt.where(Expense.date < end)
    return db.execute(stmt).all()


def overview(db: Session, user: User, start: date, end: date):
    """(groups, tags) rows of (currency, spent, received, count, id, name) in [start, end)."""
    base = (
        select(Group.currency, spent(), received(), func.count())
        .select_from(Expense)
        .join(Expense.group)
        .where(Group.owner_id == user.id, Expense.date >= start, Expense.date < end)
    )
    groups = db.execute(
        base.add_columns(Group.id, Group.name).group_by(Group.id, Group.name, Group.currency)
    ).all()
    tags = db.execute(
        base.join(expense_tags, expense_tags.c.expense_id == Expense.id)
        .join(Tag, Tag.id == expense_tags.c.tag_id)
        .add_columns(Tag.id, Tag.name)
        .group_by(Tag.id, Tag.name, Group.currency)
    ).all()
    return groups, tags
