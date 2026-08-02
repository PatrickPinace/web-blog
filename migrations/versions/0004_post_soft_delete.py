"""post: deleted_at (kosz)

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-02

Usuwanie wpisu z panelu przestaje być nieodwracalne — zamiast
DELETE od razu, wpis dostaje deleted_at i trafia do kosza, skąd można
go przywrócić albo usunąć trwale.
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("post", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_post_deleted_at", "post", ["deleted_at"], unique=False)


def downgrade():
    op.drop_index("ix_post_deleted_at", table_name="post")
    op.drop_column("post", "deleted_at")
