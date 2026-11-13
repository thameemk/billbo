from __future__ import annotations

from decimal import Decimal
from uuid import UUID

import pycountry
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from app.api.dependencies import NOT_FOUND, UNAUTHORIZED, get_current_user
from app.db.session import get_db
from app.models import Group, User
from app.services import groups as svc
from app.utils.pagination import Page

router = APIRouter(prefix="/api/v1/groups", tags=["groups"], responses=UNAUTHORIZED)


def check_currency(value: str) -> str:
    value = value.upper()
    if pycountry.currencies.get(alpha_3=value) is None:
        raise ValueError("Enter a valid ISO 4217 currency code")
    return value


class GroupCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=120)
    currency: str = Field("INR", min_length=3, max_length=3, description="ISO 4217 code, e.g. INR")

    _check_currency = field_validator("currency")(check_currency)


class GroupUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(None, min_length=1, max_length=120)
    currency: str | None = Field(
        None,
        min_length=3,
        max_length=3,
        description="ISO 4217 code; relabels the amounts, nothing is converted",
    )

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str | None) -> str | None:
        return value if value is None else check_currency(value)


class GroupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    currency: str


class GroupSummary(GroupResponse):
    spent: Decimal = Field(description="Sum of debits")
    received: Decimal = Field(description="Sum of credits, as a positive number")
    expense_count: int


@router.post("", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
def create_group(
    payload: GroupCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Group:
    return svc.create_group(db, user, name=payload.name, currency=payload.currency)


@router.patch("/{group_id}", response_model=GroupResponse, responses=NOT_FOUND)
def update_group(
    group_id: UUID,
    payload: GroupUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Group:
    group = svc.get_owned_group(db, group_id, user)
    return svc.update_group(db, group, payload.model_dump(exclude_none=True))


@router.get("", response_model=Page[GroupSummary])
def list_groups(
    cursor: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    page = svc.list_groups(db, user, cursor, limit)
    page["items"] = [
        GroupSummary(**GroupResponse.model_validate(g).model_dump(), **totals)
        for g, totals in page["items"]
    ]
    return page


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT, responses=NOT_FOUND)
def delete_group(
    group_id: UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> None:
    svc.delete_group(db, svc.get_owned_group(db, group_id, user))
