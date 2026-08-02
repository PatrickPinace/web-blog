"""Wyszukiwanie po wpisach: dokładne dopasowanie, z fuzzy fallbackiem.

Dwuetapowe, tak jak w klub-tenisowy (apps/users/api/views.py) — najpierw
zwykłe dopasowanie podciągu (szybkie, przewidywalne), a dopiero gdy to
zwróci zero wyników, fallback na podobieństwo trigramowe, żeby literówka
w zapytaniu ("wyceniejsz" zamiast "wycenisz") wciąż znalazła coś sensownego.
Liczone w Pythonie, nie w SQL (pg_trgm) — dla skali tego blogu (dziesiątki,
może setki wpisów) skan w pamięci jest wystarczający i nie wymaga
rozszerzenia Postgresa; przy realnie dużej bazie wpisów warto to przenieść
do bazy (TrigramSimilarity), ale to inny próg skali niż mamy teraz.
"""
import unicodedata

_PL_MAP = str.maketrans("ąćęłńóśźż", "acelnoszz")

_FUZZY_THRESHOLD = 0.3
_MIN_FUZZY_TOKEN_LEN = 4


def normalize(text):
    """Małe litery, bez polskich ogonków i innych diakrytyków (NFD)."""
    text = text.lower().translate(_PL_MAP)
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )


def _trigrams(s):
    if len(s) < 3:
        return {s}
    padded = f"  {s} "
    return {padded[i : i + 3] for i in range(len(padded) - 2)}


def trigram_similarity(a, b):
    """Podobieństwo Jaccarda na trigramach — 0.0 (nic wspólnego) do 1.0 (identyczne)."""
    if not a or not b:
        return 0.0
    if len(a) < 2 or len(b) < 2:
        return 1.0 if a == b else 0.0
    ta, tb = _trigrams(a), _trigrams(b)
    union = ta | tb
    return len(ta & tb) / len(union) if union else 0.0


def _haystack_words(post):
    """Słowa, po których wpis jest przeszukiwany: tytuł, excerpt, tagi."""
    parts = [post.title, post.excerpt or ""] + [t.name for t in post.tags]
    return normalize(" ".join(parts)).split()


def search_posts(posts, query):
    """Filtruje listę Post po `query`. Zwraca podzbiór `posts`, bez zmiany kolejności
    przy dopasowaniu substring; przy fallbacku fuzzy sortuje wg trafności.

    `posts` to już lista (nie query) — wywołujący ma odfiltrować status
    published PRZED wywołaniem tej funkcji (patrz published_posts_query()
    w app/public/queries.py), żeby szkice nigdy nie wpadły w wynik.
    """
    tokens = normalize(query).split()
    if not tokens:
        return []

    exact = []
    for post in posts:
        haystack = " ".join(_haystack_words(post))
        if all(t in haystack for t in tokens):
            exact.append(post)
    if exact:
        return exact

    fuzzy_tokens = [t for t in tokens if len(t) >= _MIN_FUZZY_TOKEN_LEN]
    if not fuzzy_tokens:
        return []

    scored = []
    for post in posts:
        words = _haystack_words(post)
        if not words:
            continue
        token_scores = [
            max((trigram_similarity(t, w) for w in words), default=0.0)
            for t in fuzzy_tokens
        ]
        if all(score >= _FUZZY_THRESHOLD for score in token_scores):
            scored.append((sum(token_scores), post))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [post for _, post in scored]
