"""
Migrate sessions to store SHA-256 token hashes (SEC-VULN-002).

Revision ID: 003
Revises: 002
Create Date: 2026-11-10
"""
import hashlib

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: str = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add nullable token_hash column
    op.add_column("sessions", sa.Column("token_hash", sa.String(64), nullable=True))

    # 2. Backfill existing active sessions safely by computing SHA-256 of plaintext token
    bind = op.get_bind()
    sessions_table = sa.table(
        "sessions",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("token", sa.String(128)),
        sa.column("token_hash", sa.String(64)),
    )
    rows = bind.execute(sa.select(sessions_table.c.id, sessions_table.c.token)).fetchall()
    for row in rows:
        if row.token:
            h = hashlib.sha256(row.token.encode("utf-8")).hexdigest()
            bind.execute(
                sessions_table.update()
                .where(sessions_table.c.id == row.id)
                .values(token_hash=h)
            )

    # 3. Enforce NOT NULL on token_hash now that existing rows are populated
    op.alter_column("sessions", "token_hash", nullable=False)

    # 4. Create unique index on token_hash
    op.create_index("ix_sessions_token_hash", "sessions", ["token_hash"], unique=True)

    # 5. Drop old plaintext token index and column
    op.drop_index("ix_sessions_token", table_name="sessions")
    op.drop_column("sessions", "token")


def downgrade() -> None:
    # 1. Recreate nullable token column
    op.add_column("sessions", sa.Column("token", sa.String(128), nullable=True))

    # 2. Drop unique index on token_hash
    op.drop_index("ix_sessions_token_hash", table_name="sessions")

    # 3. Drop token_hash column
    op.drop_column("sessions", "token_hash")

    # 4. Recreate index on token
    op.create_index("ix_sessions_token", "sessions", ["token"], unique=True)
