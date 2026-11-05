"""allow negative expense amounts: positive is a debit, negative a credit

Revision ID: c4a8d2f6e1b7
Revises: e19a4c7b3f52
Create Date: 2026-11-05 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op

revision: str = "c4a8d2f6e1b7"
down_revision: Union[str, None] = "e19a4c7b3f52"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("ck_expenses_amount_positive", "expenses", type_="check")
    op.create_check_constraint("ck_expenses_amount_nonzero", "expenses", "amount <> 0")


def downgrade() -> None:
    # fails while credit rows exist: they have no representation in the old schema
    op.drop_constraint("ck_expenses_amount_nonzero", "expenses", type_="check")
    op.create_check_constraint("ck_expenses_amount_positive", "expenses", "amount > 0")
