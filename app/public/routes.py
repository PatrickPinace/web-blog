from flask import render_template, request
from sqlalchemy.orm import joinedload

from app.models import Post, Tag
from app.public import public_bp
from app.public.feed import build_rss_feed
from app.public.queries import (
    POSTS_PER_PAGE,
    get_blog_stats,
    get_branches,
    get_neighbours,
    get_published_post_or_404,
    get_top_tags,
    promote_scheduled_posts,
    published_posts_query,
)
from app.utils.content import add_heading_ids
from app.utils.embeds import render_embeds
from app.utils.search import search_posts


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
    branch = request.args.get("branza", "").strip()

    query = published_posts_query()
    if branch:
        query = query.filter(Post.branch == branch)

    pagination = query.paginate(page=page, per_page=POSTS_PER_PAGE, error_out=False)
    return render_template(
        "public/index.html",
        pagination=pagination,
        tags=get_top_tags(),
        branches=get_branches(),
        active_branch=branch,
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

    top_tags = get_top_tags()
    # Wybrany tag musi być widoczny jako aktywny filtr na własnej stronie,
    # nawet jeśli nie należy do top N — inaczej pasek filtrów "gubi"
    # aktualnie przeglądany tag, jeśli ktoś trafił tu z linku spoza top N
    # (np. z /tagi albo bezpośredniego adresu).
    if tag not in top_tags:
        top_tags = [*top_tags, tag]

    return render_template(
        "public/tag_detail.html",
        tag=tag,
        pagination=pagination,
        tags=top_tags,
    )


@public_bp.route("/tagi")
def tags():
    """Pełna lista tagów jako punkt wejścia — inaczej trzeba je odkrywać
    jeden po drugim, klikając na wpisy, które je mają."""
    promote_scheduled_posts()
    all_tags = (
        Tag.query.filter(
            Tag.posts.any(status=Post.STATUS_PUBLISHED, deleted_at=None)
        )
        .order_by(Tag.name)
        .all()
    )
    return render_template("public/tags.html", tags=all_tags)


@public_bp.route("/szukaj")
def search():
    query = request.args.get("q", "").strip()
    results = []
    if query:
        candidates = (
            published_posts_query().options(joinedload(Post.tags)).all()
        )
        results = search_posts(candidates, query)
    return render_template("public/search.html", query=query, results=results)


@public_bp.route("/about")
def about():
    return render_template("public/about.html")


@public_bp.route("/feed.xml")
def feed():
    return build_rss_feed()
