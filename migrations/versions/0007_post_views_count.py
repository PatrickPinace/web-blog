"""post: views_count (licznik wyświetleń)

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-21

Orientacyjny licznik odwiedzin wpisu, inkrementowany przy /post/<slug>
z deduplikacją przez cookie sesyjne — patrz record_view() w
app/public/queries.py.
"""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "post",
        sa.Column("views_count", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade():
    op.drop_column("post", "views_count")
