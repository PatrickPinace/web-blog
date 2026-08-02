from flask import render_template, request

from app.models import Post, Tag
from app.public import public_bp
from app.public.feed import build_rss_feed
from app.public.queries import (
    POSTS_PER_PAGE,
    get_blog_stats,
    get_neighbours,
    get_published_post_or_404,
    published_posts_query,
)
from app.utils.content import add_heading_ids
from app.utils.embeds import render_embeds


def render_post_body(post):
    """Przygotowuje treść do wyświetlenia: embedy, potem id nagłówków.

    Kolejność jest istotna. `render_embeds` wstawia iframe'y z placeholderów,
    a `add_heading_ids` dokleja kotwice do nagłówków — obie operacje działają
    na już zsanityzowanym `body_html` i tylko w locie, nic tu nie wraca
    do bazy. Zwraca (html, spis_treści).
    """
    return add_heading_ids(render_embeds(post.body_html))


@public_bp.route("/")
def index():
    page = request.args.get("page", 1, type=int)
    pagination = published_posts_query().paginate(
        page=page, per_page=POSTS_PER_PAGE, error_out=False
    )
    return render_template(
        "public/index.html",
        pagination=pagination,
        tags=Tag.query.order_by(Tag.name).all(),
        stats=get_blog_stats(),
    )


@public_bp.route("/post/<slug>")
def post_detail(slug):
    post = get_published_post_or_404(slug)
    body_html, headings = render_post_body(post)
    previous, following = get_neighbours(post)
    return render_template(
        "public/post_detail.html",
        post=post,
        body_html=body_html,
        headings=headings,
        prev_post=previous,
        next_post=following,
    )


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
        "public/tag_detail.html",
        tag=tag,
        pagination=pagination,
        tags=Tag.query.order_by(Tag.name).all(),
    )


@public_bp.route("/about")
def about():
    return render_template("public/about.html")


@public_bp.route("/feed.xml")
def feed():
    return build_rss_feed()
