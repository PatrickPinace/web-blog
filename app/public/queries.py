from sqlalchemy import func

from app.models import Post, Tag, post_tags

POSTS_PER_PAGE = 10

# Ile tagów pokazać w pasku filtrów na stronie głównej, zanim schowamy
# resztę za linkiem do /tagi. Przy kilku tagach nie widać różnicy; przy
# kilkudziesięciu pasek nie zajmuje pół ekranu nad listą wpisów.
TOP_TAGS_LIMIT = 8


def published_posts_query():
    """Bazowe zapytanie o wpisy widoczne publicznie.

    Cały ruch publiczny MUSI przechodzić przez tę funkcję — draft nie może
    wyciec przez żadną publiczną ścieżkę, nawet po zgadnięciu sluga.
    """
    return Post.query.filter_by(status=Post.STATUS_PUBLISHED).order_by(
        Post.published_at.desc()
    )


def get_published_post_or_404(slug):
    return published_posts_query().filter_by(slug=slug).first_or_404()


def get_neighbours(post):
    """Sąsiednie wpisy w kolejności publikacji: (poprzedni, następny).

    "Poprzedni" to starszy wpis, "następny" — nowszy. Oba wychodzą
    z `published_posts_query()`, więc szkic nigdy nie pojawi się w nawigacji
    (byłby to wyciek: sam tytuł zdradzałby nieopublikowaną treść).

    Dla szkicu w podglądzie zwracamy (None, None) — wpis nie ma jeszcze
    miejsca w osi czasu.
    """
    if not post.is_published or post.published_at is None:
        return None, None

    base = Post.query.filter_by(status=Post.STATUS_PUBLISHED)

    previous = (
        base.filter(Post.published_at < post.published_at)
        .order_by(Post.published_at.desc())
        .first()
    )
    following = (
        base.filter(Post.published_at > post.published_at)
        .order_by(Post.published_at.asc())
        .first()
    )
    return previous, following


def get_blog_stats():
    """Liczby na stronę główną: ile wpisów, ile branż."""
    posts = published_posts_query().count()
    branches = (
        Post.query.filter_by(status=Post.STATUS_PUBLISHED)
        .filter(Post.branch.isnot(None), Post.branch != "")
        .with_entities(func.count(func.distinct(Post.branch)))
        .scalar()
    )
    return {"posts": posts, "branches": branches or 0}


def get_top_tags(limit=TOP_TAGS_LIMIT):
    """Najpopularniejsze tagi (po liczbie opublikowanych wpisów), do paska
    filtrów na stronie głównej. Pozostałe tagi zostają dostępne na /tagi —
    ten pasek ma być skróconą wizytówką, nie kompletną listą."""
    return (
        Tag.query.join(post_tags, Tag.id == post_tags.c.tag_id)
        .join(Post, Post.id == post_tags.c.post_id)
        .filter(Post.status == Post.STATUS_PUBLISHED)
        .group_by(Tag.id)
        .order_by(func.count(Post.id).desc(), Tag.name)
        .limit(limit)
        .all()
    )


def get_branches():
    """Unikalne branże opublikowanych wpisów, z licznikiem, do filtra."""
    rows = (
        Post.query.filter_by(status=Post.STATUS_PUBLISHED)
        .filter(Post.branch.isnot(None), Post.branch != "")
        .with_entities(Post.branch, func.count(Post.id))
        .group_by(Post.branch)
        .order_by(Post.branch)
        .all()
    )
    return [{"name": name, "count": count} for name, count in rows]
