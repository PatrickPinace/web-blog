"""post_revision (wersjonowanie treści wpisu)

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-21

Snapshot title/excerpt/body_source tuż PRZED zapisaniem zmiany treści —
rozszerza post_activity (który zna tylko nazwy zmienionych pól) o realne
wartości, żeby dało się zobaczyć różnicę i przywrócić starszą wersję.
Patrz docstring PostRevision w app/models.py.
"""
from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "post_revision",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("excerpt", sa.String(length=500), nullable=True),
        sa.Column("body_source", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["post.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
    )
    op.create_index(
        "ix_post_revision_post_id", "post_revision", ["post_id"], unique=False
    )


def downgrade():
    op.drop_index("ix_post_revision_post_id", table_name="post_revision")
    op.drop_table("post_revision")
