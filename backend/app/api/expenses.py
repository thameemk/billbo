from __future__ import annotations

from datetime import date as Date
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, WithJsonSchema, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session, contains_eager

from app.api.dependencies import NOT_FOUND, UNAUTHORIZED, get_current_user
from app.api.groups import GroupResponse, get_owned_group
from app.api.tags import TagResponse
from app.db.session import get_db
from app.models import Expense, Group, Tag, User
from app.utils.pagination import Page, paginate

router = APIRouter(prefix="/api/v1/expenses", tags=["expenses"], responses=UNAUTHORIZED)


def require_string(value):
    # a JSON number would pass through a float; money travels as a string
    if not isinstance(value, str):
        raise ValueError('Send the amount as a string, e.g. "12.50"')
    return value


# positive = debit, negative = credit
Amount = Annotated[
    Decimal,
    BeforeValidator(require_string),
    WithJsonSchema({"type": "string", "examples": ["12.50"], "title": "Amount"}),
]


class ExpenseUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=255)
    notes: str | None = Field(default=None, max_length=2000)
    amount: Amount = Field(max_digits=12, decimal_places=2)
    date: Date
    tags: list[Annotated[str, Field(min_length=1, max_length=30)]] = Field(
        default=[], max_length=10
    )

    @field_validator("amount")
    @classmethod
    def check_amount(cls, amount: Decimal) -> Decimal:
        if amount == 0:
            raise ValueError("Amount must not be zero")
        return amount

    @field_validator("tags", mode="before")
    @classmethod
    def clean_tags(cls, tags):
        # trim, lowercase and drop duplicates (keeping order) so "Food" and "food " are one tag
        if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
            return tags
        return list(dict.fromkeys(t.strip().lower() for t in tags if t.strip()))


def set_tags(expense: Expense, names: list[str], user: User, db: Session) -> None:
    """Point the expense at the caller's tags with these names, creating the missing ones."""
    found = {
        t.name: t
        for t in db.scalars(select(Tag).where(Tag.owner_id == user.id, Tag.name.in_(names)))
    }
    expense.tags = [found.get(n) or Tag(owner_id=user.id, name=n) for n in names]


class ExpenseCreate(ExpenseUpdate):
    group_id: UUID


class ExpenseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    group_id: UUID
    title: str
    notes: str | None
    amount: Decimal
    date: Date
    tags: list[TagResponse]
    updated_at: datetime
    group: GroupResponse | None = None  # only with ?include=group


def to_response(expense: Expense, with_group: bool = False) -> ExpenseResponse:
    # built by hand so that expense.group is never lazy-loaded unless asked for;
    # group is left unset otherwise, so exclude_unset drops it from the JSON
    extra = {"group": GroupResponse.model_validate(expense.group)} if with_group else {}
    return ExpenseResponse(
        id=expense.id,
        group_id=expense.group_id,
        title=expense.title,
        notes=expense.notes,
        amount=expense.amount,
        date=expense.date,
        tags=[TagResponse.model_validate(t) for t in expense.tags],
        updated_at=expense.updated_at,
        **extra,
    )


@router.post(
    "",
    response_model=ExpenseResponse,
    response_model_exclude_unset=True,
    status_code=status.HTTP_201_CREATED,
    responses=NOT_FOUND,
)
def create_expense(
    payload: ExpenseCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExpenseResponse:
    get_owned_group(payload.group_id, user, db)  # 404 unless it is the caller's group
    expense = Expense(**payload.model_dump(exclude={"tags"}))
    set_tags(expense, payload.tags, user, db)
    db.add(expense)
    db.commit()
    return to_response(expense)


def filtered(
    stmt, group_id: UUID | None, tag_id: UUID | None, q: str | None, user: User, db: Session
):
    if group_id:
        get_owned_group(group_id, user, db)  # 404 unless it is the caller's group
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


@router.get(
    "", response_model=Page[ExpenseResponse], response_model_exclude_unset=True, responses=NOT_FOUND
)
def list_expenses(
    group_id: UUID | None = None,
    tag_id: UUID | None = None,
    q: str | None = Query(None, max_length=100),  # matches title or tag name
    include: Literal["group"] | None = None,
    cursor: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = filtered(select(Expense), group_id, tag_id, q, user, db)
    if include:
        stmt = stmt.options(contains_eager(Expense.group))
    page = paginate(db, stmt, (Expense.date, Expense.created_at), Expense, cursor, limit)
    page["items"] = [to_response(e, with_group=bool(include)) for e in page["items"]]
    return page


class MonthTotal(BaseModel):
    month: str = Field(pattern=r"^\d{4}-\d{2}$", description="YYYY-MM")
    currency: str = Field(description="ISO 4217 code of the group the expenses belong to")
    spent: Decimal = Field(description="Sum of debits")
    received: Decimal = Field(description="Sum of credits, as a positive number")


class MonthTotals(BaseModel):
    items: list[MonthTotal]


@router.get("/monthly", response_model=MonthTotals, responses=NOT_FOUND)
def monthly_totals(
    group_id: UUID | None = None,
    tag_id: UUID | None = None,
    q: str | None = Query(None, max_length=100),
    start: Date | None = Query(None, alias="from", description="Inclusive start date"),
    end: Date | None = Query(None, alias="to", description="Exclusive end date"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Per-month totals over everything the filters match within [from, to), not just a page."""
    month = func.to_char(Expense.date, "YYYY-MM")
    spent = func.coalesce(func.sum(Expense.amount).filter(Expense.amount > 0), 0)
    received = func.coalesce(-func.sum(Expense.amount).filter(Expense.amount < 0), 0)
    stmt = filtered(
        select(month, Group.currency, spent, received), group_id, tag_id, q, user, db
    ).group_by(month, Group.currency)
    if start:
        stmt = stmt.where(Expense.date >= start)
    if end:
        stmt = stmt.where(Expense.date < end)
    return {
        "items": [
            MonthTotal(month=m, currency=c, spent=s, received=r) for m, c, s, r in db.execute(stmt)
        ]
    }


def get_owned_expense(expense_id: UUID, user: User, db: Session) -> Expense:
    expense = db.scalar(
        select(Expense)
        .join(Expense.group)
        .where(Expense.id == expense_id, Group.owner_id == user.id)
    )
    if expense is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    return expense


@router.put(
    "/{expense_id}",
    response_model=ExpenseResponse,
    response_model_exclude_unset=True,
    responses=NOT_FOUND,
)
def update_expense(
    expense_id: UUID,
    payload: ExpenseUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExpenseResponse:
    expense = get_owned_expense(expense_id, user, db)
    for field, value in payload.model_dump(exclude={"tags"}).items():
        setattr(expense, field, value)
    set_tags(expense, payload.tags, user, db)
    expense.updated_at = func.now()  # onupdate alone misses tag-only edits
    db.commit()
    return to_response(expense)


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT, responses=NOT_FOUND)
def delete_expense(
    expense_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    db.delete(get_owned_expense(expense_id, user, db))
    db.commit()
