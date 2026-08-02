"""post_activity (log historii zmian wpisu)

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-02

Lekki log kto/kiedy/co zrobił z wpisem (akcja + nazwy zmienionych pól,
bez wartości) — nie pełne wersjonowanie, patrz docstring PostActivity.
"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "post_activity",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("changed_fields", sa.String(length=300), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["post.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
    )
    op.create_index(
        "ix_post_activity_post_id", "post_activity", ["post_id"], unique=False
    )


def downgrade():
    op.drop_index("ix_post_activity_post_id", table_name="post_activity")
    op.drop_table("post_activity")
