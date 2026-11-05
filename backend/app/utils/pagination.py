from __future__ import annotations

import base64
import binascii
import json
from typing import Generic, TypeVar
from uuid import UUID

from fastapi import HTTPException, status
from pydantic import BaseModel
from sqlalchemy import Select, tuple_
from sqlalchemy.orm import Session

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    next_cursor: str | None = None


def paginate(db: Session, stmt: Select, sort_cols: tuple, model, cursor: str | None, limit: int):
    """Keyset pagination, newest first, on (*sort_cols, id): stable under inserts, O(limit).

    sort_cols must be non-null date/datetime columns of model, which must have a UUID `id`.
    """
    keys = (*sort_cols, model.id)
    if cursor:
        try:
            *vals, row_id = json.loads(base64.urlsafe_b64decode(cursor))
            after = (
                *(
                    c.type.python_type.fromisoformat(v)
                    for c, v in zip(sort_cols, vals, strict=True)
                ),
                UUID(row_id),
            )
            stmt = stmt.where(tuple_(*keys) < after)
        except ValueError, TypeError, binascii.Error:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid cursor") from None
    rows = list(db.scalars(stmt.order_by(*(k.desc() for k in keys)).limit(limit + 1)).all())
    next_cursor = None
    if len(rows) > limit:
        rows = rows[:limit]
        last = rows[-1]
        key = json.dumps([*(getattr(last, c.key).isoformat() for c in sort_cols), str(last.id)])
        next_cursor = base64.urlsafe_b64encode(key.encode()).decode()
    return {"items": rows, "next_cursor": next_cursor}
