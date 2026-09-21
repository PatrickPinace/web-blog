"""Rzeczy wyliczane z treści wpisu w locie: czas czytania i spis treści.

Świadomie nie trzymamy tego w bazie. Jedno źródło prawdy to `body_html`;
gdyby czas czytania albo lista nagłówków były osobnymi kolumnami, przy
każdej edycji trzeba by pamiętać o ich przeliczeniu — a przy pierwszym
zapomnieniu zaczęłyby kłamać.
"""
import re
from datetime import UTC

# Średnie tempo czytania po polsku. Zaokrąglamy w górę, minimum 1 minuta —
# "0 min czytania" wygląda na błąd, nie na krótki wpis.
_WORDS_PER_MINUTE = 200

_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")

# Pierwszy obraz z treści — jedyne dostępne źródło og:image, bo Image.post_id
# nigdy nie jest wypełniane (upload przez Quill wstawia gołe <img>, bez
# powiązania z Post — patrz app/admin/routes.py: upload_image_endpoint).
_IMG_SRC_RE = re.compile(r'<img\b[^>]*\bsrc="([^"]+)"', re.IGNORECASE)

# Każdy <img> z treści, do doklejenia loading/decoding przy renderze — Quill
# nigdy nie generuje tych atrybutów, więc nie trzeba sprawdzać duplikatów.
_IMG_TAG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)

# Nagłówki H2/H3 z treści. H1 pomijamy — tytuł wpisu jest w nagłówku strony,
# nie w treści, więc w spisie treści byłby zdublowany.
_TABLE_RE = re.compile(r"(<table\b[^>]*>.*?</table>)", re.IGNORECASE | re.DOTALL)

_HEADING_RE = re.compile(
    r"<(h[23])(\s[^>]*)?>(.*?)</\1>", re.IGNORECASE | re.DOTALL
)

# Znaki dozwolone w id nagłówka. Reszta leci — id trafia do atrybutu HTML
# i do href="#...", więc nie może zawierać cudzysłowów ani nawiasów.
_ID_UNSAFE_RE = re.compile(r"[^a-z0-9]+")

_PL_MAP = str.maketrans("ąćęłńóśźż", "acelnoszz")

# Słowa-klucze łapiące najpopularniejsze crawlery i narzędzia HTTP. Nie jest
# to lista wyczerpująca (i nie musi być) — cel to odsianie oczywistych botów
# z licznika wyświetleń, nie dokładna klasyfikacja ruchu.
_BOT_USER_AGENT_RE = re.compile(
    r"bot|crawl|spider|curl|wget|python-requests|facebookexternalhit|"
    r"slackbot|discordbot|telegrambot|whatsapp|preview",
    re.IGNORECASE,
)


# Margines między published_at i updated_at, żeby mikrosekundy odstępu
# między dwoma wywołaniami utcnow() (jedno w Post.publish(), drugie
# w onupdate przy flush) nie liczyły się jako "zaktualizowano".
_UPDATED_AFTER_PUBLISH_THRESHOLD_SECONDS = 60


def was_updated_after_publish(post):
    """True, jeśli wpis został realnie edytowany po pierwszej publikacji."""
    if post.published_at is None:
        return False
    published_at, updated_at = post.published_at, post.updated_at
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=UTC)
    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=UTC)
    delta = (updated_at - published_at).total_seconds()
    return delta > _UPDATED_AFTER_PUBLISH_THRESHOLD_SECONDS


def time_ago_pl(dt):
    """Czas względny po polsku: "przed chwilą", "3 dni temu", "2 miesiące temu".

    `dt` bez tzinfo jest traktowane jako UTC — SQLite (dev/testy) nie
    zachowuje strefy mimo DateTime(timezone=True), tak jak w
    app/admin/routes.py (dashboard_stats: oldest_draft_days).
    """
    from app.models import utcnow

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    days = (utcnow() - dt).days

    if days < 1:
        return "przed chwilą"
    if days < 30:
        return f"{days} {pluralize_pl(days, 'dzień', 'dni', 'dni')} temu"
    if days < 365:
        months = days // 30
        return f"{months} {pluralize_pl(months, 'miesiąc', 'miesiące', 'miesięcy')} temu"
    years = days // 365
    return f"{years} {pluralize_pl(years, 'rok', 'lata', 'lat')} temu"


def pluralize_pl(count, singular, plural_few, plural_many):
    """Polska odmiana liczebnikowa: 1 wpis, 2-4 wpisy, 5+ wpisów.

    Reguła: forma "few" dla liczb kończących się na 2-4, ALE nie dla
    11-14 (te idą do "many", jak w "11 wpisów", "22 wpisy", "112 wpisów").
    Działa dla dowolnej nieujemnej liczby całkowitej, nie tylko < 100.
    """
    if count == 1:
        return singular
    last_two = count % 100
    last_digit = count % 10
    if last_digit in (2, 3, 4) and last_two not in (12, 13, 14):
        return plural_few
    return plural_many


def is_bot_user_agent(user_agent):
    """True dla User-Agentów rozpoznanych jako bot/crawler/narzędzie HTTP.

    Puste/brakujące User-Agent też liczymy jako bota — prawdziwe przeglądarki
    zawsze je wysyłają, więc brak jest sam w sobie podejrzany.
    """
    if not user_agent:
        return True
    return bool(_BOT_USER_AGENT_RE.search(user_agent))


def add_image_loading_attrs(html):
    """Dokleja loading="lazy" decoding="async" do każdego <img> w treści.

    Wstawiane przy renderze, tym samym wzorcem co render_embeds/wrap_tables —
    sanitizer (bleach) nie przepuszcza tych atrybutów, więc nie mogą trafić
    do zapisanego body_html; dopisujemy je dopiero na wyjściu.
    """
    if not html:
        return html

    def _add_attrs(match):
        tag = match.group(0)
        closing = "/>" if tag.endswith("/>") else ">"
        return tag[: -len(closing)] + f' loading="lazy" decoding="async"{closing}'

    return _IMG_TAG_RE.sub(_add_attrs, html)


def first_image_url(html):
    """URL pierwszego obrazu w treści, albo None gdy wpis nie ma żadnego."""
    if not html:
        return None
    match = _IMG_SRC_RE.search(html)
    return match.group(1) if match else None


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



def wrap_tables(html):
    """Dodaje lokalny kontener przewijania wokół tabel z edytora.

    Quill zapisuje gołe ``<table>``. Wrapper powstaje dopiero przy renderze,
    więc nie zmieniamy zapisanej treści ani whitelisty sanitizera.
    """
    return _TABLE_RE.sub(r'<div class="table-wrapper">\1</div>', html or "")


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
