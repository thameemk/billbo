"""rename expense description to title, add notes

Revision ID: e19a4c7b3f52
Revises: a3d7e91c4b20
Create Date: 2026-11-04 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "e19a4c7b3f52"
down_revision: Union[str, None] = "a3d7e91c4b20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("expenses", "description", new_column_name="title")
    op.add_column("expenses", sa.Column("notes", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("expenses", "notes")
    op.alter_column("expenses", "title", new_column_name="description")
