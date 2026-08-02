"""Rzeczy wyliczane z treści wpisu w locie: czas czytania i spis treści.

Świadomie nie trzymamy tego w bazie. Jedno źródło prawdy to `body_html`;
gdyby czas czytania albo lista nagłówków były osobnymi kolumnami, przy
każdej edycji trzeba by pamiętać o ich przeliczeniu — a przy pierwszym
zapomnieniu zaczęłyby kłamać.
"""
import re

# Średnie tempo czytania po polsku. Zaokrąglamy w górę, minimum 1 minuta —
# "0 min czytania" wygląda na błąd, nie na krótki wpis.
_WORDS_PER_MINUTE = 200

_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")

# Nagłówki H2/H3 z treści. H1 pomijamy — tytuł wpisu jest w nagłówku strony,
# nie w treści, więc w spisie treści byłby zdublowany.
_HEADING_RE = re.compile(
    r"<(h[23])(\s[^>]*)?>(.*?)</\1>", re.IGNORECASE | re.DOTALL
)

# Znaki dozwolone w id nagłówka. Reszta leci — id trafia do atrybutu HTML
# i do href="#...", więc nie może zawierać cudzysłowów ani nawiasów.
_ID_UNSAFE_RE = re.compile(r"[^a-z0-9]+")

_PL_MAP = str.maketrans("ąćęłńóśźż", "acelnoszz")


def strip_tags(html):
    """Goły tekst z fragmentu HTML — do liczenia słów i tekstu nagłówków."""
    if not html:
        return ""
    return _WHITESPACE_RE.sub(" ", _TAG_RE.sub(" ", html)).strip()


def read_time(html):
    """Szacowany czas czytania w minutach (zawsze co najmniej 1)."""
    words = len(strip_tags(html).split())
    if words == 0:
        return 1
    return max(1, -(-words // _WORDS_PER_MINUTE))


def _heading_id(text, used):
    """Buduje id z tekstu nagłówka, unikalne w obrębie wpisu."""
    base = _ID_UNSAFE_RE.sub("-", text.lower().translate(_PL_MAP)).strip("-")
    base = base[:60] or "sekcja"

    candidate = base
    suffix = 2
    while candidate in used:
        candidate = f"{base}-{suffix}"
        suffix += 1
    used.add(candidate)
    return candidate


def add_heading_ids(html):
    """Dokleja `id` do H2/H3 i zwraca (html, [{id, text, level}, ...]).

    Działa na już zsanityzowanym `body_html`, tuż przed renderowaniem —
    tym samym wzorcem co `render_embeds`. W bazie nie trzymamy id, bo
    zależą od kolejności nagłówków, a ta zmienia się przy każdej edycji.

    Wstawiana wartość pochodzi wyłącznie z naszego alfabetu [a-z0-9-]
    (patrz `_ID_UNSAFE_RE`), więc nie może rozerwać atrybutu ani tagu.
    """
    if not html:
        return html, []

    headings = []
    used = set()

    def _replace(match):
        tag, attrs, inner = match.group(1), match.group(2) or "", match.group(3)
        text = strip_tags(inner)
        if not text:
            return match.group(0)

        # Nagłówek z własnym id zostawiamy w spokoju — nie nadpisujemy tego,
        # co mogło przyjść z treści, tylko pomijamy go w spisie.
        if re.search(r"\bid\s*=", attrs, re.IGNORECASE):
            return match.group(0)

        heading_id = _heading_id(text, used)
        headings.append({"id": heading_id, "text": text, "level": tag.lower()})
        return f'<{tag}{attrs} id="{heading_id}">{inner}</{tag}>'

    return _HEADING_RE.sub(_replace, html), headings
