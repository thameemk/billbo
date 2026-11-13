from __future__ import annotations

from datetime import date as Date
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, WithJsonSchema, field_validator
from sqlalchemy.orm import Session

from app.api.dependencies import NOT_FOUND, UNAUTHORIZED, get_current_user
from app.api.groups import GroupResponse
from app.api.tags import TagResponse
from app.db.session import get_db
from app.models import Expense, User
from app.services import expenses as svc
from app.utils.pagination import Page

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
    return to_response(svc.create_expense(db, user, **payload.model_dump()))


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
    page = svc.list_expenses(
        db,
        user,
        group_id=group_id,
        tag_id=tag_id,
        q=q,
        with_group=bool(include),
        cursor=cursor,
        limit=limit,
    )
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
    rows = svc.monthly_totals(db, user, group_id=group_id, tag_id=tag_id, q=q, start=start, end=end)
    return {"items": [MonthTotal(month=m, currency=c, spent=s, received=r) for m, c, s, r in rows]}


class Breakdown(BaseModel):
    id: UUID
    name: str
    currency: str
    spent: Decimal = Field(description="Sum of debits")
    received: Decimal = Field(description="Sum of credits, as a positive number")
    expense_count: int


class Overview(BaseModel):
    groups: list[Breakdown]
    tags: list[Breakdown] = Field(description="One row per tag and currency")


@router.get("/overview", response_model=Overview)
def overview(
    start: Date = Query(alias="from", description="Inclusive start date"),
    end: Date = Query(alias="to", description="Exclusive end date"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Per-group and per-tag totals within [from, to); empty ones are left out."""
    groups, tags = svc.overview(db, user, start, end)

    def rows(result):
        return sorted(
            (
                Breakdown(id=i, name=n, currency=c, spent=s, received=r, expense_count=k)
                for c, s, r, k, i, n in result
            ),
            key=lambda b: (b.name.lower(), b.currency),
        )

    return {"groups": rows(groups), "tags": rows(tags)}


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
    expense = svc.get_owned_expense(db, expense_id, user)
    return to_response(svc.update_expense(db, expense, user, **payload.model_dump()))


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT, responses=NOT_FOUND)
def delete_expense(
    expense_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    svc.delete_expense(db, svc.get_owned_expense(db, expense_id, user))
