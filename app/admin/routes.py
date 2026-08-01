from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.admin import admin_bp
from app.admin.forms import DeletePostForm, LoginForm, PostForm
from app.extensions import db, limiter
from app.models import Post, Tag, User
from app.utils.sanitize import SANITIZER_VERSION, sanitize_html
from app.utils.slugify import slugify, unique_slug

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
    query = Post.query.order_by(Post.created_at.desc())
    if status_filter in (Post.STATUS_DRAFT, Post.STATUS_PUBLISHED):
        query = query.filter_by(status=status_filter)
    posts = query.all()
    delete_form = DeletePostForm()
    return render_template(
        "admin/dashboard.html",
        posts=posts,
        status_filter=status_filter,
        delete_form=delete_form,
    )


@admin_bp.route("/post/new", methods=["GET", "POST"])
@login_required
def post_new():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(author_id=current_user.id)
        _apply_form_to_post(form, post, is_new=True)
        db.session.add(post)
        db.session.commit()
        flash("Wpis utworzony.", "success")
        return redirect(url_for("admin.dashboard"))
    return render_template("admin/post_form.html", form=form, post=None)


@admin_bp.route("/post/<int:post_id>/edit", methods=["GET", "POST"])
@login_required
def post_edit(post_id):
    post = Post.query.get_or_404(post_id)
    form = PostForm(obj=post)
    if request.method == "GET":
        form.tags.data = ", ".join(tag.name for tag in post.tags)

    if form.validate_on_submit():
        _apply_form_to_post(form, post, is_new=False)
        db.session.commit()
        flash("Wpis zapisany.", "success")
        return redirect(url_for("admin.dashboard"))
    return render_template("admin/post_form.html", form=form, post=post)


@admin_bp.route("/post/<int:post_id>/preview")
@login_required
def post_preview(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template("public/post_detail.html", post=post, is_preview=True)


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


def _apply_form_to_post(form, post, is_new):
    was_published = post.status == Post.STATUS_PUBLISHED
    title_changed = is_new or post.title != form.title.data

    post.title = form.title.data
    post.excerpt = form.excerpt.data

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
