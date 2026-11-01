"""session expiry index, drop revoked_at

Revision ID: a3d7e91c4b20
Revises: f82f1e542568
Create Date: 2026-11-01 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "a3d7e91c4b20"
down_revision: Union[str, None] = "f82f1e542568"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Revoked sessions are now deleted on logout; drop any left over
    op.execute("DELETE FROM user_sessions WHERE revoked_at IS NOT NULL")
    op.drop_column("user_sessions", "revoked_at")
    op.drop_index("ix_user_sessions_user_id", table_name="user_sessions")
    op.create_index(
        "ix_user_sessions_user_id_expires_at", "user_sessions", ["user_id", "expires_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_user_sessions_user_id_expires_at", table_name="user_sessions")
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
    op.add_column(
        "user_sessions", sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True)
    )
