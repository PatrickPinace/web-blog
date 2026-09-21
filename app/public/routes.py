from flask import Response, current_app, jsonify, make_response, render_template, request, url_for
from sqlalchemy import text
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models import Post, Tag
from app.public import public_bp
from app.public.feed import build_rss_feed
from app.public.sitemap import build_sitemap
from app.public.queries import (
    POSTS_PER_PAGE,
    VIEWED_POSTS_COOKIE,
    get_blog_build_series_posts,
    get_branches,
    get_case_studies_by_branch,
    get_kind_counts,
    get_neighbours,
    get_published_post_or_404,
    get_related_posts,
    get_series_neighbours,
    get_top_tags,
    promote_scheduled_posts,
    published_posts_query,
    record_view,
)
from app.utils.content import (
    add_heading_ids,
    add_image_loading_attrs,
    first_image_url,
    was_updated_after_publish,
    wrap_tables,
)
from app.utils.embeds import render_embeds
from app.utils.search import search_posts


def render_post_body(post):
    """Przygotowuje treść do wyświetlenia: embedy, potem id nagłówków.

    Kolejność jest istotna. `render_embeds` wstawia iframe'y z placeholderów,
    a `add_heading_ids` dokleja kotwice do nagłówków — obie operacje działają
    na już zsanityzowanym `body_html` i tylko w locie, nic tu nie wraca
    do bazy. Zwraca (html, spis_treści).
    """
    html = add_image_loading_attrs(wrap_tables(render_embeds(post.body_html)))
    return add_heading_ids(html)


@public_bp.route("/")
def index():
    page = request.args.get("page", 1, type=int)
    branch = request.args.get("branza", "").strip()
    kind = request.args.get("typ", "").strip()

    query = published_posts_query()
    if branch:
        query = query.filter(Post.branch == branch)
    if kind in Post.KINDS:
        query = query.filter(Post.kind == kind)
    else:
        kind = ""

    pagination = query.paginate(page=page, per_page=POSTS_PER_PAGE, error_out=False)
    return render_template(
        "public/index.html",
        pagination=pagination,
        active_branch=branch,
        active_kind=kind,
        kind_counts=get_kind_counts(),
        branches=get_branches(),
        series_posts=get_blog_build_series_posts(),
    )


@public_bp.route("/realizacje")
def case_studies():
    return render_template(
        "public/case_studies.html",
        branch_groups=get_case_studies_by_branch(),
    )


@public_bp.route("/post/<slug>")
def post_detail(slug):
    post = get_published_post_or_404(slug)
    body_html, headings = render_post_body(post)
    series_posts = get_blog_build_series_posts()
    previous, following = get_series_neighbours(post, series_posts)
    navigation_kind = (
        "series" if any(series_post.id == post.id for series_post in series_posts) else "chronological"
    )
    if navigation_kind == "chronological":
        previous, following = get_neighbours(post)

    base_url = current_app.config["BLOG_BASE_URL"].rstrip("/")
    post_url = f"{base_url}{url_for('public.post_detail', slug=post.slug)}"

    response = make_response(render_template(
        "public/post_detail.html",
        post=post,
        body_html=body_html,
        headings=headings,
        prev_post=previous,
        next_post=following,
        navigation_kind=navigation_kind,
        related_posts=get_related_posts(post),
        post_url=post_url,
        og_image_url=first_image_url(post.body_html),
        was_updated_after_publish=was_updated_after_publish(post),
    ))

    viewed = record_view(post)
    if viewed is not None:
        response.set_cookie(VIEWED_POSTS_COOKIE, ",".join(viewed), httponly=True, samesite="Lax")
    return response


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


@public_bp.route("/szukaj/live")
def search_live():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify(results=[])

    candidates = published_posts_query().options(joinedload(Post.tags)).all()
    results = search_posts(candidates, query)[:8]
    return jsonify(
        results=[
            {
                "title": post.title,
                "excerpt": post.excerpt,
                "url": url_for("public.post_detail", slug=post.slug),
            }
            for post in results
        ]
    )


@public_bp.route("/about")
def about():
    return render_template("public/about.html", series_posts=get_blog_build_series_posts())


@public_bp.route("/feed.xml")
def feed():
    return build_rss_feed()


@public_bp.route("/sitemap.xml")
def sitemap():
    return build_sitemap()


@public_bp.route("/robots.txt")
def robots():
    base_url = current_app.config["BLOG_BASE_URL"].rstrip("/")
    body = (
        "User-agent: *\n"
        "Disallow: /admin/\n"
        f"Sitemap: {base_url}{url_for('public.sitemap')}\n"
    )
    return Response(body, mimetype="text/plain")


@public_bp.route("/portfolio.json")
def portfolio_json():
    """Realizacje jako ustrukturyzowany JSON — dla kogoś, kto woli sprawdzić
    portfolio przez curl niż przeklikać stronę po stronie."""
    base_url = current_app.config["BLOG_BASE_URL"].rstrip("/")
    posts = published_posts_query().filter(Post.kind == Post.KIND_CASE_STUDY).all()
    return jsonify(
        realizacje=[
            {
                "title": post.title,
                "branch": post.branch,
                "excerpt": post.excerpt,
                "is_concept": post.is_concept,
                "url": f"{base_url}{url_for('public.post_detail', slug=post.slug)}",
                "published_at": post.published_at.isoformat(),
            }
            for post in posts
        ]
    )


@public_bp.route("/healthz")
def healthz():
    """Sprawdzenie gotowości dla hostingu (keep-alive ping, restart po awarii).

    Weryfikuje samo połączenie z bazą, nie logikę aplikacji — jeśli baza nie
    odpowiada, nie ma sensu udawać, że serwis żyje.
    """
    try:
        db.session.execute(text("SELECT 1"))
    except Exception:
        return jsonify(status="error"), 503
    return jsonify(status="ok")
