"""user: is_demo (konto pokazowe dla odwiedzających)

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-22

Rozróżnia konto demo (edycja treści, ale bez uploadu obrazków i bez
niszczenia struktury) od właściwego admina — patrz @demo_forbidden
w app/admin/routes.py i app/demo.py.
"""
from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "user",
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade():
    op.drop_column("user", "is_demo")
