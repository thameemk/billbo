from __future__ import annotations

import uuid
from datetime import date as dt_date
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import TimestampMixin


class Group(TimestampMixin, Base):
    __tablename__ = "groups"
    __table_args__ = (
        CheckConstraint("currency ~ '^[A-Z]{3}$'", name="ck_groups_currency_format"),
        Index(
            "ix_groups_owner_id_created_at", "owner_id", text("created_at DESC"), text("id DESC")
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(120))
    currency: Mapped[str] = mapped_column(String(3), default="INR")

    expenses: Mapped[list["Expense"]] = relationship(
        "Expense", back_populates="group", cascade="all, delete-orphan"
    )


class Tag(Base):
    __tablename__ = "tags"
    __table_args__ = (UniqueConstraint("owner_id", "name", name="uq_tags_owner_id_name"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(30))


expense_tags = Table(
    "expense_tags",
    Base.metadata,
    Column("expense_id", ForeignKey("expenses.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
    Index("ix_expense_tags_tag_id", "tag_id"),
)


class Expense(TimestampMixin, Base):
    __tablename__ = "expenses"
    __table_args__ = (
        CheckConstraint("amount <> 0", name="ck_expenses_amount_nonzero"),
        Index("ix_expenses_group_id_date", "group_id", text("date DESC"), text("id DESC")),
        Index(
            "ix_expenses_group_id_date_amount", "group_id", "date", postgresql_include=["amount"]
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))  # positive = debit, negative = credit
    date: Mapped[dt_date]

    group: Mapped["Group"] = relationship("Group", back_populates="expenses")
    tags: Mapped[list[Tag]] = relationship(
        secondary=expense_tags, order_by=Tag.name, lazy="selectin"
    )
