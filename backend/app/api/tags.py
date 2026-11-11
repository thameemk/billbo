from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import NOT_FOUND, UNAUTHORIZED, get_current_user
from app.db.session import get_db
from app.models import Tag, User

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
    # unpaginated, a person's tag list stays small; paginate if it ever doesn't
    return {
        "items": db.scalars(select(Tag).where(Tag.owner_id == user.id).order_by(Tag.name)).all()
    }


class TagBody(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=30)

    @field_validator("name")
    @classmethod
    def lowercase(cls, name: str) -> str:
        return name.lower()  # same normalisation as tags typed on an expense


def ensure_name_free(name: str, user: User, db: Session) -> None:
    if db.scalar(select(Tag.id).where(Tag.owner_id == user.id, Tag.name == name)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tag already exists")


@router.post(
    "", response_model=TagResponse, status_code=status.HTTP_201_CREATED, responses=CONFLICT
)
def create_tag(
    payload: TagBody, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Tag:
    ensure_name_free(payload.name, user, db)
    tag = Tag(owner_id=user.id, name=payload.name)
    db.add(tag)
    db.commit()
    return tag


@router.patch("/{tag_id}", response_model=TagResponse, responses=NOT_FOUND | CONFLICT)
def update_tag(
    tag_id: UUID,
    payload: TagBody,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Tag:
    tag = db.get(Tag, tag_id)
    if tag is None or tag.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")
    if payload.name != tag.name:
        ensure_name_free(payload.name, user, db)
        tag.name = payload.name
        db.commit()
    return tag


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT, responses=NOT_FOUND)
def delete_tag(
    tag_id: UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> None:
    tag = db.get(Tag, tag_id)
    if tag is None or tag.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")
    db.delete(tag)  # expense_tags rows cascade; the expenses stay, just untagged
    db.commit()
