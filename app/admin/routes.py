from datetime import UTC
from urllib.parse import urlparse

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from flask import abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.admin import admin_bp
from app.admin.forms import (
    DeleteLabelForm,
    DeletePostForm,
    LabelForm,
    LoginForm,
    PostForm,
    PostStatusForm,
)
from app.extensions import db, limiter
from app.models import Image, Label, Post, Tag, User, utcnow
from app.public.routes import render_post_body
from app.utils.embeds import build_youtube_placeholder
from app.utils.sanitize import SANITIZER_VERSION, sanitize_html
from app.utils.search import search_posts
from app.utils.slugify import slugify, unique_slug
from app.utils.uploads import UploadError, is_allowed_image_url, upload_image

_hasher = PasswordHasher()


@admin_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is not None and _verify_password(user, form.password.data):
            login_user(user)
            return redirect(url_for("admin.dashboard"))
        flash("Nieprawidłowa nazwa użytkownika lub hasło.", "error")

    return render_template("admin/login.html", form=form)


def _verify_password(user, password):
    try:
        return _hasher.verify(user.password_hash, password)
    except VerifyMismatchError:
        return False


@admin_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("admin.login"))


@admin_bp.route("/")
@login_required
def dashboard():
    status_filter = request.args.get("status")
    kind_filter = request.args.get("kind")
    branch_filter = request.args.get("branch")
    search_query = request.args.get("q", "").strip()

    query = Post.query.order_by(Post.created_at.desc())
    if status_filter in (Post.STATUS_DRAFT, Post.STATUS_PUBLISHED):
        query = query.filter_by(status=status_filter)
    if kind_filter in Post.KINDS:
        query = query.filter_by(kind=kind_filter)
    elif branch_filter:
        query = query.filter_by(branch=branch_filter)
    posts = query.all()

    if search_query:
        posts = search_posts(posts, search_query)

    delete_form = DeletePostForm()
    status_form = PostStatusForm()
    return render_template(
        "admin/dashboard.html",
        posts=posts,
        status_filter=status_filter,
        kind_filter=kind_filter,
        branch_filter=branch_filter,
        search_query=search_query,
        branches=_dashboard_branches(),
        kinds=Post.KINDS,
        stats=_dashboard_stats(),
        delete_form=delete_form,
        status_form=status_form,
    )


@admin_bp.route("/post/new", methods=["GET", "POST"])
@login_required
def post_new():
    form = PostForm()
    form.labels.choices = _label_choices()
    if form.validate_on_submit():
        post = Post(author_id=current_user.id, title="", slug="")
        db.session.add(post)
        _apply_form_to_post(form, post, is_new=True)
        db.session.commit()
        flash("Wpis utworzony.", "success")
        return redirect(url_for("admin.dashboard"))
    return render_template("admin/post_form.html", form=form, post=None)


@admin_bp.route("/post/<int:post_id>/edit", methods=["GET", "POST"])
@login_required
def post_edit(post_id):
    post = Post.query.get_or_404(post_id)
    form = PostForm(obj=post)
    form.labels.choices = _label_choices()
    if request.method == "GET":
        form.tags.data = ", ".join(tag.name for tag in post.tags)
        form.labels.data = [label.id for label in post.labels]

    if form.validate_on_submit():
        _apply_form_to_post(form, post, is_new=False)
        db.session.commit()
        flash("Wpis zapisany.", "success")
        return redirect(url_for("admin.dashboard"))
    return render_template("admin/post_form.html", form=form, post=post)


@admin_bp.route("/post/<int:post_id>/duplicate", methods=["POST"])
@login_required
def post_duplicate(post_id):
    form = DeletePostForm()
    if not form.validate_on_submit():
        abort(400)
    original = Post.query.get_or_404(post_id)

    title = f"{original.title} (kopia)"
    copy = Post(
        author_id=current_user.id,
        title=title,
        slug=unique_slug(slugify(title), lambda s: Post.query.filter_by(slug=s).first() is not None),
        excerpt=original.excerpt,
        kind=original.kind,
        branch=original.branch,
        is_concept=original.is_concept,
        body_source=original.body_source,
        body_html=original.body_html,
        sanitizer_version=original.sanitizer_version,
        status=Post.STATUS_DRAFT,
        tags=list(original.tags),
        labels=list(original.labels),
    )
    db.session.add(copy)
    db.session.commit()
    flash("Wpis zduplikowany jako szkic.", "success")
    return redirect(url_for("admin.post_edit", post_id=copy.id))


def _label_choices():
    return [(label.id, label.name) for label in Label.query.order_by(Label.name).all()]


def _dashboard_branches():
    """Branże wszystkich wpisów (w tym szkiców) — inaczej niż get_branches()
    na stronie publicznej, która celowo liczy tylko opublikowane."""
    rows = (
        Post.query.filter(Post.branch.isnot(None), Post.branch != "")
        .with_entities(Post.branch)
        .distinct()
        .order_by(Post.branch)
        .all()
    )
    return [row[0] for row in rows]


def _dashboard_stats():
    """Liczone od WSZYSTKICH wpisów, niezależnie od aktywnego filtra —
    orientacja "ile mam ogółem", nie "ile w przefiltrowanym widoku"."""
    draft_count = Post.query.filter_by(status=Post.STATUS_DRAFT).count()
    published_count = Post.query.filter_by(status=Post.STATUS_PUBLISHED).count()
    oldest_draft = (
        Post.query.filter_by(status=Post.STATUS_DRAFT)
        .order_by(Post.updated_at.asc())
        .first()
    )
    oldest_draft_days = None
    if oldest_draft is not None:
        updated_at = oldest_draft.updated_at
        # SQLite (testy, dev) nie zachowuje tzinfo mimo DateTime(timezone=True) —
        # traktujemy odczytaną wartość bez strefy jako UTC, tak jak zapisana.
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=UTC)
        oldest_draft_days = (utcnow() - updated_at).days
    return {
        "draft_count": draft_count,
        "published_count": published_count,
        "oldest_draft": oldest_draft,
        "oldest_draft_days": oldest_draft_days,
    }


def _safe_admin_redirect(target):
    """request.referrer to nagłówek kontrolowany przez klienta — przekierowanie
    tylko na lokalną ścieżkę w /admin/, nigdy wprost na dowolny URL z niego."""
    if target:
        parsed = urlparse(target)
        if parsed.path.startswith("/admin/"):
            return parsed.path + (f"?{parsed.query}" if parsed.query else "")
    return url_for("admin.dashboard")


@admin_bp.route("/post/<int:post_id>/preview")
@login_required
def post_preview(post_id):
    post = Post.query.get_or_404(post_id)
    # Ten sam szablon co publicznie, więc musi dostać komplet danych.
    # Sąsiadów nie pokazujemy — szkic nie ma miejsca w osi publikacji.
    body_html, headings = render_post_body(post)
    return render_template(
        "public/post_detail.html",
        post=post,
        body_html=body_html,
        headings=headings,
        prev_post=None,
        next_post=None,
        is_preview=True,
    )


@admin_bp.route("/post/<int:post_id>/delete", methods=["POST"])
@login_required
def post_delete(post_id):
    form = DeletePostForm()
    if not form.validate_on_submit():
        abort(400)
    post = Post.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    flash("Wpis usunięty.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/post/<int:post_id>/toggle-status", methods=["POST"])
@login_required
def post_toggle_status(post_id):
    form = PostStatusForm()
    if not form.validate_on_submit():
        abort(400)
    post = Post.query.get_or_404(post_id)
    if post.is_published:
        post.unpublish()
        flash("Wpis wrócił do szkiców.", "success")
    else:
        post.publish()
        flash("Wpis opublikowany.", "success")
    db.session.commit()
    return redirect(_safe_admin_redirect(request.referrer))


@admin_bp.route("/labels", methods=["GET", "POST"])
@login_required
def labels():
    form = LabelForm()
    if form.validate_on_submit():
        name = form.name.data.strip()
        if Label.query.filter_by(name=name).first() is not None:
            flash(f"Znaczek „{name}” już istnieje.", "error")
        else:
            label = Label(
                name=name,
                color=form.color.data,
                slug=unique_slug(
                    slugify(name),
                    lambda s: Label.query.filter_by(slug=s).first() is not None,
                ),
            )
            db.session.add(label)
            db.session.commit()
            flash("Znaczek dodany.", "success")
        return redirect(url_for("admin.labels"))

    all_labels = Label.query.order_by(Label.name).all()
    return render_template(
        "admin/labels.html",
        form=form,
        labels=all_labels,
        delete_form=DeleteLabelForm(),
    )


@admin_bp.route("/labels/<int:label_id>/edit", methods=["POST"])
@login_required
def label_edit(label_id):
    label = Label.query.get_or_404(label_id)
    form = LabelForm()
    if form.validate_on_submit():
        name = form.name.data.strip()
        existing = Label.query.filter(
            Label.name == name, Label.id != label.id
        ).first()
        if existing is not None:
            flash(f"Znaczek „{name}” już istnieje.", "error")
        else:
            if name != label.name:
                label.slug = unique_slug(
                    slugify(name),
                    lambda s: Label.query.filter(
                        Label.slug == s, Label.id != label.id
                    ).first()
                    is not None,
                )
            label.name = name
            label.color = form.color.data
            db.session.commit()
            flash("Znaczek zapisany.", "success")
    return redirect(url_for("admin.labels"))


@admin_bp.route("/labels/<int:label_id>/delete", methods=["POST"])
@login_required
def label_delete(label_id):
    form = DeleteLabelForm()
    if not form.validate_on_submit():
        abort(400)
    label = Label.query.get_or_404(label_id)
    db.session.delete(label)
    db.session.commit()
    flash("Znaczek usunięty.", "success")
    return redirect(url_for("admin.labels"))


@admin_bp.route("/upload-image", methods=["POST"])
@login_required
@limiter.limit("30 per hour")
def upload_image_endpoint():
    """Przyjmuje plik z panelu i odsyła URL z Cloudinary do wstawienia w treść."""
    try:
        public_id, url = upload_image(request.files.get("file"))
    except UploadError as exc:
        return jsonify({"error": str(exc)}), 400

    db.session.add(Image(cloudinary_public_id=public_id, url=url))
    db.session.commit()
    return jsonify({"url": url})


@admin_bp.route("/embed-youtube", methods=["POST"])
@login_required
def embed_youtube_endpoint():
    """Zamienia URL filmu na placeholder embedu (iframe powstaje przy renderze)."""
    html = build_youtube_placeholder((request.form or {}).get("url", ""))
    if html is None:
        return jsonify({"error": "To nie jest prawidłowy adres filmu na YouTube."}), 400
    return jsonify({"html": html})


@admin_bp.route("/check-image-url", methods=["POST"])
@login_required
def check_image_url_endpoint():
    """Weryfikuje, że wklejony URL obrazka pochodzi z dozwolonej domeny."""
    url = (request.form or {}).get("url", "").strip()
    if not is_allowed_image_url(url):
        return jsonify(
            {"error": "Dozwolone są tylko obrazki z zaufanych domen (np. Cloudinary)."}
        ), 400
    return jsonify({"url": url})


def _apply_form_to_post(form, post, is_new):
    was_published = post.status == Post.STATUS_PUBLISHED
    title_changed = is_new or post.title != form.title.data

    post.title = form.title.data
    post.excerpt = form.excerpt.data
    post.kind = form.kind.data
    post.branch = (form.branch.data or "").strip() or None
    post.is_concept = bool(form.is_concept.data)
    post.labels = Label.query.filter(Label.id.in_(form.labels.data or [])).all()

    # Kolejność zapisu jest obowiązkowa (plan, sekcja 5): body_source
    # najpierw bez zmian, potem body_html = sanitize(body_source).
    post.body_source = form.body_source.data or ""
    post.body_html = sanitize_html(post.body_source)
    post.sanitizer_version = SANITIZER_VERSION

    if title_changed:
        base_slug = slugify(form.title.data)
        post.slug = unique_slug(
            base_slug,
            lambda s: Post.query.filter(
                Post.slug == s, Post.id != (post.id or -1)
            ).first()
            is not None,
        )

    post.tags = _resolve_tags(form.tags.data)

    post.status = form.status.data
    if post.status == Post.STATUS_PUBLISHED and not was_published:
        post.publish()


def _resolve_tags(raw_tags):
    names = [t.strip() for t in (raw_tags or "").split(",") if t.strip()]
    tags = []
    for name in names:
        tag = Tag.query.filter_by(name=name).first()
        if tag is None:
            tag = Tag(name=name, slug=unique_slug(
                slugify(name),
                lambda s: Tag.query.filter_by(slug=s).first() is not None,
            ))
            db.session.add(tag)
        tags.append(tag)
    return tags
