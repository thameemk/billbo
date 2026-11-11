"""covering index so per-month totals are an index-only scan

Revision ID: d5b2f8a3c961
Revises: c4a8d2f6e1b7
Create Date: 2026-11-11 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op

revision: str = "d5b2f8a3c961"
down_revision: Union[str, None] = "c4a8d2f6e1b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_expenses_group_id_date_amount",
        "expenses",
        ["group_id", "date"],
        postgresql_include=["amount"],
    )


def downgrade() -> None:
    op.drop_index("ix_expenses_group_id_date_amount", table_name="expenses")
