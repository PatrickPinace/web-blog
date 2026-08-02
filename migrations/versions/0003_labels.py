"""label, post_labels

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-02

Wyróżnione znaczki na wpisie, zarządzane w panelu — użytkownik dodaje
własne (nazwa + kolor z małej palety), niezależnie od tematycznych Tag.
`is_concept` na Post zostaje bez zmian, to osobna, stała semantyka.
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "label",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=40), nullable=False),
        sa.Column("slug", sa.String(length=60), nullable=False),
        sa.Column("color", sa.String(length=20), nullable=False),
    )
    op.create_index("ix_label_name", "label", ["name"], unique=True)
    op.create_index("ix_label_slug", "label", ["slug"], unique=True)

    op.create_table(
        "post_labels",
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("label_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["post.id"]),
        sa.ForeignKeyConstraint(["label_id"], ["label.id"]),
        sa.PrimaryKeyConstraint("post_id", "label_id"),
    )


def downgrade():
    op.drop_table("post_labels")
    op.drop_index("ix_label_slug", table_name="label")
    op.drop_index("ix_label_name", table_name="label")
    op.drop_table("label")
