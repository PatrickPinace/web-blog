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

post_labels = db.Table(
    "post_labels",
    db.Column("post_id", db.Integer, db.ForeignKey("post.id"), primary_key=True),
    db.Column("label_id", db.Integer, db.ForeignKey("label.id"), primary_key=True),
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
    STATUS_SCHEDULED = "scheduled"
    STATUS_PUBLISHED = "published"

    KIND_CASE_STUDY = "realizacja"
    KIND_NOTE = "notatka"
    KIND_ESSAY = "felieton"
    KINDS = (KIND_CASE_STUDY, KIND_NOTE, KIND_ESSAY)

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(220), unique=True, nullable=False, index=True)

    # Typ wpisu — rozdziela opisy realizacji od notatek technicznych.
    # Widoczny na liście jako etykieta, filtruje charakter treści.
    kind = db.Column(
        db.String(20), nullable=False, default=KIND_CASE_STUDY, index=True
    )

    # Branża klienta ("gastronomia", "usługi lokalne"). Tylko dla realizacji,
    # przy notatkach zwykle puste.
    branch = db.Column(db.String(80), nullable=True)

    # Czy to projekt koncepcyjny (fikcyjny klient), a nie prawdziwe wdrożenie.
    # Wymóg uczciwości wobec czytelnika: takie wpisy są jawnie oznaczone
    # w interfejsie — patrz workdir/brief-design.md.
    is_concept = db.Column(db.Boolean, nullable=False, default=False)

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

    # Kiedy wpis ma się sam opublikować. Sprawdzane leniwie — patrz
    # promote_scheduled_posts() w app/public/queries.py — nie ma osobnego
    # procesu (Celery/cron), bo hosting go nie udźwignie. Wystarczy, że wpis
    # "dojrzewa" przy najbliższym publicznym odczycie listy wpisów po terminie.
    scheduled_for = db.Column(db.DateTime(timezone=True), nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    # Usunięcie z panelu jest odwracalne (kosz) — wpis dostaje deleted_at
    # zamiast znikać od razu z bazy. Trwałe usunięcie to osobna, świadoma
    # akcja tylko z widoku kosza.
    deleted_at = db.Column(db.DateTime(timezone=True), nullable=True, index=True)

    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    author = db.relationship("User", back_populates="posts")

    tags = db.relationship(
        "Tag", secondary=post_tags, back_populates="posts", order_by="Tag.name"
    )
    labels = db.relationship(
        "Label", secondary=post_labels, back_populates="posts", order_by="Label.name"
    )
    images = db.relationship(
        "Image", back_populates="post", cascade="all, delete-orphan"
    )
    activity = db.relationship(
        "PostActivity",
        back_populates="post",
        cascade="all, delete-orphan",
        order_by="PostActivity.created_at.desc()",
    )

    @property
    def is_published(self):
        return self.status == self.STATUS_PUBLISHED

    @property
    def is_deleted(self):
        return self.deleted_at is not None

    def soft_delete(self):
        # STATUS_DRAFT na wszelki wypadek — usunięty wpis nie ma prawa
        # przejść przez published_posts_query() nawet gdyby ktoś kiedyś
        # zapomniał dopisać filtra po deleted_at. scheduled_for czyścimy
        # z tego samego powodu co przy unpublish — bez tego kosz pokazywałby
        # mylącą, nieaktualną datę planowanej publikacji.
        self.status = self.STATUS_DRAFT
        self.scheduled_for = None
        self.deleted_at = utcnow()

    def restore(self):
        self.deleted_at = None

    def publish(self):
        if self.published_at is None:
            self.published_at = utcnow()
        self.status = self.STATUS_PUBLISHED
        self.scheduled_for = None

    def unpublish(self):
        # published_at zostaje nietknięte — to data PIERWSZEJ publikacji,
        # nie flaga "aktualnie widoczny". Ponowna publikacja jej nie zmienia.
        self.status = self.STATUS_DRAFT
        self.scheduled_for = None

    def schedule(self, when):
        self.status = self.STATUS_SCHEDULED
        self.scheduled_for = when

    def __repr__(self):
        return f"<Post {self.slug!r} ({self.status})>"


class PostActivity(db.Model):
    """Lekki log historii: kto/kiedy/co zrobił z wpisem, bez treści.

    Świadomie nie jest to wersjonowanie (brak zapisanych wartości pól,
    tylko ich nazwy) — to prostsza, tańsza odpowiedź na "coś tu ostatnio
    zmieniłem, ale co". Pełne wersjonowanie zostaje w planach jako osobna,
    większa funkcja, sensowna dopiero jeśli to okaże się niewystarczające.
    """

    ACTION_CREATED = "created"
    ACTION_UPDATED = "updated"
    ACTION_PUBLISHED = "published"
    ACTION_UNPUBLISHED = "unpublished"
    ACTION_SCHEDULED = "scheduled"
    ACTION_DELETED = "deleted"
    ACTION_RESTORED = "restored"
    ACTION_DUPLICATED = "duplicated"

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    action = db.Column(db.String(20), nullable=False)
    # Nazwy zmienionych pól oddzielone przecinkiem (np. "title,body_source"),
    # nie ich wartości — patrz docstring klasy. Puste dla akcji bez pól
    # (usunięto/przywrócono/zduplikowano).
    changed_fields = db.Column(db.String(300), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    post = db.relationship("Post", back_populates="activity")
    user = db.relationship("User")

    def __repr__(self):
        return f"<PostActivity post_id={self.post_id} {self.action!r}>"


class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False, index=True)

    posts = db.relationship("Post", secondary=post_tags, back_populates="tags")

    def __repr__(self):
        return f"<Tag {self.slug!r}>"


class Label(db.Model):
    """Wyróżnione znaczki na wpisie (jak dawne `is_concept`), zarządzane
    w panelu — inne niż Tag: nie opisują tematu, tylko sygnalizują coś
    o samym wpisie ("eksperyment", "do aktualizacji"). `is_concept` na
    Post to osobna, stała semantyka uczciwości i nie jest tym zastępowana.
    """

    COLORS = ("blue", "purple", "green", "amber", "red", "gray")
    DEFAULT_COLOR = "blue"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(40), unique=True, nullable=False)
    slug = db.Column(db.String(60), unique=True, nullable=False, index=True)
    color = db.Column(db.String(20), nullable=False, default=DEFAULT_COLOR)

    posts = db.relationship("Post", secondary=post_labels, back_populates="labels")

    def __repr__(self):
        return f"<Label {self.slug!r}>"


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
