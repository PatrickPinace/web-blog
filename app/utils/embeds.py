import re
from urllib.parse import parse_qs, urlparse

# Dozwolone hosty filmów. Dopasowanie jest dokładne (po znormalizowaniu
# "www."), nie przez `in` / `endswith` — inaczej `youtube.com.evil.tld`
# albo `evil-youtube.com` przeszłyby walidację.
_YOUTUBE_HOSTS = frozenset({"youtube.com", "m.youtube.com", "youtube-nocookie.com"})
_YOUTUBE_SHORT_HOSTS = frozenset({"youtu.be"})

# ID filmu na YouTube: 11 znaków z bezpiecznego alfabetu. Walidujemy je
# osobno, bo trafia wprost do generowanego przez nas URL-a.
_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")

EMBED_BASE_URL = "https://www.youtube-nocookie.com/embed/"


def extract_youtube_id(url):
    """Zwraca ID filmu, jeśli URL wskazuje na YouTube. W innym razie None.

    Nie wykonuje ŻADNEGO zapytania sieciowego — adres podany przez admina
    jest wyłącznie parsowany. Pobranie zasobu po stronie serwera byłoby
    wektorem SSRF (adres mógłby wskazywać na sieć wewnętrzną hostingu).
    """
    if not url:
        return None

    try:
        parsed = urlparse(url.strip())
    except ValueError:
        return None

    if parsed.scheme not in ("http", "https"):
        return None

    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]

    if host in _YOUTUBE_SHORT_HOSTS:
        candidate = parsed.path.lstrip("/")
    elif host in _YOUTUBE_HOSTS:
        if parsed.path == "/watch":
            candidate = (parse_qs(parsed.query).get("v") or [""])[0]
        elif parsed.path.startswith(("/embed/", "/v/", "/shorts/")):
            candidate = parsed.path.split("/", 2)[2]
        else:
            return None
    else:
        return None

    candidate = candidate.split("/")[0]
    return candidate if _VIDEO_ID_RE.match(candidate) else None


def build_youtube_placeholder(url):
    """Buduje PLACEHOLDER embedu do wstawienia w edytorze. None dla obcych URL-i.

    Nie zwraca `<iframe>`, bo treść z edytora przechodzi przez bleach, który
    iframe wycina (i ma wycinać — nie przyjmujemy go od użytkownika).
    Zamiast tego zapisujemy nieszkodliwy znacznik z samym ID filmu:

        <div class="embed-responsive" data-youtube-id="dQw4w9WgXcQ"></div>

    Dopiero przy renderowaniu `render_embeds()` zamienia go na prawdziwy
    iframe. Dzięki temu w bazie nigdy nie ma osadzonego kodu ramki, a ID
    jest walidowane dwukrotnie: przy zapisie i przy renderowaniu.
    """
    video_id = extract_youtube_id(url)
    if video_id is None:
        return None
    return f'<div class="embed-responsive" data-youtube-id="{video_id}"></div>'


_PLACEHOLDER_RE = re.compile(
    r'<div class="embed-responsive" data-youtube-id="([A-Za-z0-9_-]{11})"></div>'
)


def render_embeds(html):
    """Zamienia placeholdery na zaufane iframe'y tuż przed wyświetleniem.

    Wywoływane na już zsanityzowanym `body_html`. ID jest ponownie
    sprawdzane wzorcem, więc nawet ręczna modyfikacja bazy nie pozwoli
    wstrzyknąć nic poza 11 znakami z bezpiecznego alfabetu.
    """
    if not html:
        return html

    def _replace(match):
        video_id = match.group(1)
        if not _VIDEO_ID_RE.match(video_id):
            return ""
        return (
            f'<div class="embed-responsive">'
            f'<iframe src="{EMBED_BASE_URL}{video_id}" title="YouTube" '
            f'loading="lazy" allowfullscreen '
            f'referrerpolicy="strict-origin-when-cross-origin"></iframe>'
            f"</div>"
        )

    return _PLACEHOLDER_RE.sub(_replace, html)
