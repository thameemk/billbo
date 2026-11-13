from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from app.api.dependencies import NOT_FOUND, UNAUTHORIZED, get_current_user
from app.db.session import get_db
from app.models import Tag, User
from app.services import tags as svc

router = APIRouter(prefix="/api/v1/tags", tags=["tags"], responses=UNAUTHORIZED)
CONFLICT = {409: {"description": "A tag with that name already exists"}}


class TagResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str


class TagList(BaseModel):
    items: list[TagResponse]


@router.get("", response_model=TagList)
def list_tags(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"items": svc.list_tags(db, user)}


class TagBody(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=30)

    @field_validator("name")
    @classmethod
    def lowercase(cls, name: str) -> str:
        return name.lower()  # same normalisation as tags typed on an expense


@router.post(
    "", response_model=TagResponse, status_code=status.HTTP_201_CREATED, responses=CONFLICT
)
def create_tag(
    payload: TagBody, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Tag:
    return svc.create_tag(db, user, payload.name)


@router.patch("/{tag_id}", response_model=TagResponse, responses=NOT_FOUND | CONFLICT)
def update_tag(
    tag_id: UUID,
    payload: TagBody,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Tag:
    return svc.rename_tag(db, svc.get_owned_tag(db, tag_id, user), payload.name)


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT, responses=NOT_FOUND)
def delete_tag(
    tag_id: UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> None:
    svc.delete_tag(db, svc.get_owned_tag(db, tag_id, user))
