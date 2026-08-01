import re
import unicodedata

_SLUG_STRIP_RE = re.compile(r"[^a-z0-9]+")


def slugify(text):
    """Zamienia tytuł na slug URL, z obsługą polskich znaków (np. ą → a)."""
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = _SLUG_STRIP_RE.sub("-", ascii_text.lower()).strip("-")
    return slug or "wpis"


def unique_slug(base_slug, exists_fn):
    """Dokleja -2, -3, ... aż slug przestanie kolidować.

    `exists_fn(slug)` powinno zwrócić True, jeśli dany slug jest już zajęty.
    """
    slug = base_slug
    counter = 2
    while exists_fn(slug):
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug
