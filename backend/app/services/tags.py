from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.models import Tag, User


def list_tags(db: Session, user: User) -> list[Tag]:
    # unpaginated, a person's tag list stays small; paginate if it ever doesn't
    return list(db.scalars(select(Tag).where(Tag.owner_id == user.id).order_by(Tag.name)))


def get_owned_tag(db: Session, tag_id: UUID, user: User) -> Tag:
    tag = db.get(Tag, tag_id)
    if tag is None or tag.owner_id != user.id:
        raise NotFoundError("Tag not found")
    return tag


def _ensure_name_free(db: Session, name: str, owner_id: UUID) -> None:
    if db.scalar(select(Tag.id).where(Tag.owner_id == owner_id, Tag.name == name)):
        raise ConflictError("Tag already exists")


def commit_tags(db: Session) -> None:
    """Commit, turning a lost race on the unique tag name into a 409 instead of a 500."""
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        if "uq_tags_owner_id_name" not in str(e.orig):
            raise
        raise ConflictError("Tag already exists") from None


def create_tag(db: Session, user: User, name: str) -> Tag:
    _ensure_name_free(db, name, user.id)
    tag = Tag(owner_id=user.id, name=name)
    db.add(tag)
    commit_tags(db)
    return tag


def rename_tag(db: Session, tag: Tag, name: str) -> Tag:
    if name != tag.name:
        _ensure_name_free(db, name, tag.owner_id)
        tag.name = name
        commit_tags(db)
    return tag


def delete_tag(db: Session, tag: Tag) -> None:
    db.delete(tag)  # expense_tags rows cascade; the expenses stay, just untagged
    db.commit()
