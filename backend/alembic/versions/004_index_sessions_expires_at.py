"""
Add index on sessions.expires_at for efficient pruning (SEC-VULN-010).

Revision ID: 004
Revises: 003
Create Date: 2026-11-10
"""
from alembic import op
import sqlalchemy as sa

revision: str = "004"
down_revision: str = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_sessions_expires_at", "sessions", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_sessions_expires_at", table_name="sessions")
