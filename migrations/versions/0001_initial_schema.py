"""initial schema: user, post, tag, post_tags, image

Revision ID: 0001
Revises:
Create Date: 2026-08-01

"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False
        ),
    )
    op.create_index("ix_user_username", "user", ["username"], unique=True)

    op.create_table(
        "post",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=220), nullable=False),
        sa.Column("body_source", sa.Text(), nullable=False),
        sa.Column("body_html", sa.Text(), nullable=False),
        sa.Column("sanitizer_version", sa.Integer(), nullable=False),
        sa.Column("excerpt", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["author_id"], ["user.id"]),
    )
    op.create_index("ix_post_slug", "post", ["slug"], unique=True)
    op.create_index("ix_post_status", "post", ["status"], unique=False)

    op.create_table(
        "tag",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
    )
    op.create_index("ix_tag_name", "tag", ["name"], unique=True)
    op.create_index("ix_tag_slug", "tag", ["slug"], unique=True)

    op.create_table(
        "post_tags",
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["post.id"]),
        sa.ForeignKeyConstraint(["tag_id"], ["tag.id"]),
        sa.PrimaryKeyConstraint("post_id", "tag_id"),
    )

    op.create_table(
        "image",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cloudinary_public_id", sa.String(length=255), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("alt", sa.String(length=255), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("post_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["post_id"], ["post.id"]),
    )


def downgrade():
    op.drop_table("image")
    op.drop_table("post_tags")
    op.drop_index("ix_tag_slug", table_name="tag")
    op.drop_index("ix_tag_name", table_name="tag")
    op.drop_table("tag")
    op.drop_index("ix_post_status", table_name="post")
    op.drop_index("ix_post_slug", table_name="post")
    op.drop_table("post")
    op.drop_index("ix_user_username", table_name="user")
    op.drop_table("user")
