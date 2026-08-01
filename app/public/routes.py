from flask import render_template, request

from app.models import Post, Tag
from app.public import public_bp
from app.public.feed import build_rss_feed
from app.public.queries import (
    POSTS_PER_PAGE,
    get_published_post_or_404,
    published_posts_query,
)


@public_bp.route("/")
def index():
    page = request.args.get("page", 1, type=int)
    pagination = published_posts_query().paginate(
        page=page, per_page=POSTS_PER_PAGE, error_out=False
    )
    return render_template("public/index.html", pagination=pagination)


@public_bp.route("/post/<slug>")
def post_detail(slug):
    post = get_published_post_or_404(slug)
    return render_template("public/post_detail.html", post=post)


@public_bp.route("/tag/<slug>")
def tag_detail(slug):
    tag = Tag.query.filter_by(slug=slug).first_or_404()
    page = request.args.get("page", 1, type=int)
    pagination = (
        published_posts_query()
        .filter(Post.tags.any(id=tag.id))
        .paginate(page=page, per_page=POSTS_PER_PAGE, error_out=False)
    )
    return render_template(
        "public/tag_detail.html", tag=tag, pagination=pagination
    )


@public_bp.route("/about")
def about():
    return render_template("public/about.html")


@public_bp.route("/feed.xml")
def feed():
    return build_rss_feed()
