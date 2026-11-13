from __future__ import annotations

from sqlalchemy import func

from app.models import Expense


def spent():
    """Sum of debits."""
    return func.coalesce(func.sum(Expense.amount).filter(Expense.amount > 0), 0)


def received():
    """Sum of credits, as a positive number."""
    return func.coalesce(-func.sum(Expense.amount).filter(Expense.amount < 0), 0)
