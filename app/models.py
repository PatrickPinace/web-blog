from datetime import UTC, datetime

from flask_login import UserMixin

from app.extensions import db


def utcnow():
    return datetime.now(UTC)


post_tags = db.Table(
    "post_tags",
    db.Column("post_id", db.Integer, db.ForeignKey("post.id"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("tag.id"), primary_key=True),
)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    posts = db.relationship("Post", back_populates="author")

    def __repr__(self):
        return f"<User {self.username}>"


class Post(db.Model):
    STATUS_DRAFT = "draft"
    STATUS_PUBLISHED = "published"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(220), unique=True, nullable=False, index=True)

    # body_source: surowe wyjście edytora Quill, do ponownej edycji.
    # body_html: HTML po sanityzacji bleach — TO renderujemy publicznie.
    # Kolejność zapisu jest obowiązkowa: body_source najpierw, potem
    # body_html = sanitize(body_source). Nigdy odwrotnie. Patrz plan, sekcja 5.
    body_source = db.Column(db.Text, nullable=False, default="")
    body_html = db.Column(db.Text, nullable=False, default="")

    # Wersja reguł sanitizera, którymi wygenerowano body_html. Pozwala
    # znaleźć wpisy do przeliczenia komendą `flask resanitize` po zmianie
    # whitelisty (plan, sekcja 7).
    sanitizer_version = db.Column(db.Integer, nullable=False, default=0)

    excerpt = db.Column(db.String(500), nullable=True)
    status = db.Column(
        db.String(20), nullable=False, default=STATUS_DRAFT, index=True
    )
    published_at = db.Column(db.DateTime(timezone=True), nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    author = db.relationship("User", back_populates="posts")

    tags = db.relationship(
        "Tag", secondary=post_tags, back_populates="posts", order_by="Tag.name"
    )
    images = db.relationship(
        "Image", back_populates="post", cascade="all, delete-orphan"
    )

    @property
    def is_published(self):
        return self.status == self.STATUS_PUBLISHED

    def publish(self):
        if self.published_at is None:
            self.published_at = utcnow()
        self.status = self.STATUS_PUBLISHED

    def __repr__(self):
        return f"<Post {self.slug!r} ({self.status})>"


class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False, index=True)

    posts = db.relationship("Post", secondary=post_tags, back_populates="tags")

    def __repr__(self):
        return f"<Tag {self.slug!r}>"


class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cloudinary_public_id = db.Column(db.String(255), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    alt = db.Column(db.String(255), nullable=True)
    uploaded_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=True)
    post = db.relationship("Post", back_populates="images")

    def __repr__(self):
        return f"<Image {self.cloudinary_public_id!r}>"
