from flask import current_app, request
from sqlalchemy import func

from app.extensions import db
from app.models import Post, PostActivity, Tag, post_tags, utcnow
from app.utils.content import is_bot_user_agent

POSTS_PER_PAGE = 10

VIEWED_POSTS_COOKIE = "wb_viewed"

# Ile tagów pokazać w pasku filtrów na stronie głównej, zanim schowamy
# resztę za linkiem do /tagi. Przy kilku tagach nie widać różnicy; przy
# kilkudziesięciu pasek nie zajmuje pół ekranu nad listą wpisów.
TOP_TAGS_LIMIT = 8


def promote_scheduled_posts():
    """"Dojrzewa" zaplanowane wpisy, których termin już minął.

    Zamiast Celery/cronu (hosting go nie udźwignie) — sprawdzane leniwie,
    tuż przed każdym odczytem publicznej listy wpisów. Publish() ustawia
    published_at i czyści scheduled_for, więc wpis staje się nieodróżnialny
    od opublikowanego ręcznie.
    """
    due = Post.query.filter(
        Post.status == Post.STATUS_SCHEDULED,
        Post.scheduled_for.isnot(None),
        Post.scheduled_for <= utcnow(),
        Post.deleted_at.is_(None),
    ).all()
    if not due:
        return
    for post in due:
        post.publish()
        # user_id=None: to sam system publikuje po upływie terminu, nie
        # zalogowany admin — nie ma tu żadnego request.user do przypisania
        # (funkcja jest wołana z anonimowych, publicznych żądań czytelników).
        db.session.add(
            PostActivity(post_id=post.id, action=PostActivity.ACTION_PUBLISHED)
        )
    db.session.commit()


def published_posts_query():
    """Bazowe zapytanie o wpisy widoczne publicznie.

    Cały ruch publiczny MUSI przechodzić przez tę funkcję — draft nie może
    wyciec przez żadną publiczną ścieżkę, nawet po zgadnięciu sluga.
    """
    promote_scheduled_posts()
    return Post.query.filter_by(
        status=Post.STATUS_PUBLISHED, deleted_at=None
    ).order_by(Post.published_at.desc())


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

    base = Post.query.filter_by(status=Post.STATUS_PUBLISHED, deleted_at=None)

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


def get_blog_build_series_posts():
    """Zwraca publicznie dostępne części serii w kolejności konfiguracji.

    To wspólne źródło dla strony głównej, /about i nawigacji wpisu. Bazujemy
    na ``published_posts_query()``, więc szkice, kosz i wpisy zaplanowane na
    przyszłość nie mogą ujawnić nawet tytułu. Wpis zaplanowany na przeszłość
    jest najpierw promowany tą samą leniwą regułą co reszta części publicznej.
    """
    slugs = current_app.config.get("BLOG_BUILD_SERIES_SLUGS", ())
    if isinstance(slugs, str):
        slugs = tuple(slug.strip() for slug in slugs.split(",") if slug.strip())
    if not slugs:
        return []

    posts_by_slug = {
        post.slug: post
        for post in published_posts_query().filter(Post.slug.in_(slugs)).all()
    }
    return [posts_by_slug[slug] for slug in slugs if slug in posts_by_slug]


def get_series_neighbours(post, series_posts):
    """Zwraca sąsiadów z serii albo ``(None, None)`` poza serią."""
    for index, series_post in enumerate(series_posts):
        if series_post.id == post.id:
            previous = series_posts[index - 1] if index else None
            following = series_posts[index + 1] if index + 1 < len(series_posts) else None
            return previous, following
    return None, None


def record_view(post):
    """Liczy odwiedziny wpisu, chyba że to bot albo ten czytelnik już go
    dziś... właściwie w tej sesji przeglądarki widział.

    Deduplikacja przez cookie sesyjne (bez Max-Age — ginie z zamknięciem
    przeglądarki): jeden slug liczy się raz na sesję, więc F5 czy powrót
    nawigacją nie napompowuje licznika. To orientacyjny wskaźnik
    popularności, nie ścisła analityka — stąd brak IP/fingerprintingu.

    Zwraca zaktualizowaną listę odwiedzonych slugów do zapisania w cookie,
    albo None, jeśli nic się nie zmieniło (bot albo wpis już widziany).
    """
    if is_bot_user_agent(request.headers.get("User-Agent")):
        return None

    raw = request.cookies.get(VIEWED_POSTS_COOKIE, "")
    viewed = [slug for slug in raw.split(",") if slug]
    if post.slug in viewed:
        return None

    post.views_count += 1
    db.session.commit()

    viewed.append(post.slug)
    return viewed


RELATED_POSTS_LIMIT = 3


def get_related_posts(post, limit=RELATED_POSTS_LIMIT):
    """Inne opublikowane wpisy ze wspólnym tagiem, najnowsze najpierw.

    Bez tagów na wpisie nie ma się do czego odwołać — zwracamy puste, żeby
    strona wpisu nie dostawała losowego zestawu niepowiązanych artykułów.
    """
    if not post.tags:
        return []
    tag_ids = [tag.id for tag in post.tags]
    return (
        published_posts_query()
        .filter(Post.id != post.id, Post.tags.any(Tag.id.in_(tag_ids)))
        .limit(limit)
        .all()
    )


def get_top_tags(limit=TOP_TAGS_LIMIT):
    """Najpopularniejsze tagi (po liczbie opublikowanych wpisów), do paska
    filtrów na stronie głównej. Pozostałe tagi zostają dostępne na /tagi —
    ten pasek ma być skróconą wizytówką, nie kompletną listą."""
    return (
        Tag.query.join(post_tags, Tag.id == post_tags.c.tag_id)
        .join(Post, Post.id == post_tags.c.post_id)
        .filter(Post.status == Post.STATUS_PUBLISHED, Post.deleted_at.is_(None))
        .group_by(Tag.id)
        .order_by(func.count(Post.id).desc(), Tag.name)
        .limit(limit)
        .all()
    )


def get_kind_counts():
    """Liczba opublikowanych wpisów każdego typu (realizacja/notatka/felieton),
    do przełącznika na stronie głównej. Typy bez żadnego opublikowanego
    wpisu są pominięte — pusty filtr byłby ślepym zaułkiem dla czytelnika."""
    # order_by(None) resetuje ORDER BY published_at odziedziczony z
    # published_posts_query() — SQLite go po cichu toleruje w zapytaniu
    # z GROUP BY, ale Postgres odrzuca (kolumna spoza GROUP BY/agregacji
    # w ORDER BY jest błędem składniowym), patrz known-issues.
    counts = dict(
        published_posts_query()
        .order_by(None)
        .with_entities(Post.kind, func.count(Post.id))
        .group_by(Post.kind)
        .all()
    )
    return [(kind, counts[kind]) for kind in Post.KINDS if kind in counts]


def get_branches():
    """Branże z co najmniej jednym opublikowanym wpisem, alfabetycznie,
    do przełącznika na stronie głównej (patrz get_kind_counts — sama zasada)."""
    return [
        branch
        for branch, in (
            published_posts_query()
            .filter(Post.branch.isnot(None))
            .with_entities(Post.branch)
            .distinct()
            .order_by(Post.branch)
            .all()
        )
    ]


# Etykieta dla realizacji bez przypisanej branży — grupa zbiorcza na
# /realizacje, żeby żaden opublikowany case study nie zgubił się z widoku
# mimo brakującego pola (opcjonalnego w formularzu).
UNBRANCHED_LABEL = "inne"


def get_case_studies_by_branch():
    """Opublikowane realizacje pogrupowane po branży, alfabetycznie po
    nazwie branży (grupa "inne" na końcu), najnowsze wpisy w grupie
    najpierw — do widoku /realizacje (karta per branża)."""
    posts = (
        published_posts_query()
        .filter(Post.kind == Post.KIND_CASE_STUDY)
        .all()
    )
    groups = {}
    for post in posts:
        groups.setdefault(post.branch or UNBRANCHED_LABEL, []).append(post)

    ordered_branches = sorted(b for b in groups if b != UNBRANCHED_LABEL)
    if UNBRANCHED_LABEL in groups:
        ordered_branches.append(UNBRANCHED_LABEL)
    return [(branch, groups[branch]) for branch in ordered_branches]
