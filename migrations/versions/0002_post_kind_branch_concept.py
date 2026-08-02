"""post: kind, branch, is_concept

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-02

Pola pod widok listy realizacji (etykieta typu i branży) oraz jawne
oznaczanie wpisów koncepcyjnych — fikcyjne case study nie może udawać
prawdziwego wdrożenia.
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    # Kolumny NOT NULL dokładane do tabeli, która może już mieć wiersze —
    # stąd server_default przy dodawaniu, zdejmowany zaraz po wypełnieniu.
    op.add_column(
        "post",
        sa.Column(
            "kind",
            sa.String(length=20),
            nullable=False,
            server_default="realizacja",
        ),
    )
    op.add_column("post", sa.Column("branch", sa.String(length=80), nullable=True))
    op.add_column(
        "post",
        sa.Column(
            "is_concept",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    op.create_index("ix_post_kind", "post", ["kind"], unique=False)

    # Wartość domyślną ustala aplikacja, nie baza.
    with op.batch_alter_table("post") as batch:
        batch.alter_column("kind", server_default=None)
        batch.alter_column("is_concept", server_default=None)


def downgrade():
    op.drop_index("ix_post_kind", table_name="post")
    op.drop_column("post", "is_concept")
    op.drop_column("post", "branch")
    op.drop_column("post", "kind")
