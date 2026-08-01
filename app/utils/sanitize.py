import re

from bleach.html5lib_shim import Filter
from bleach.sanitizer import Cleaner

# Wersja reguł sanitizera. Podbij przy KAŻDEJ zmianie whitelisty poniżej —
# pozwala znaleźć wpisy do przeliczenia przez `flask resanitize`
# (plan, sekcja 7, "Procedura zmiany whitelisty").
#
# v1 (etap 4):  whitelist bazowa, bez klas Quilla i bez embedów.
# v2 (etap 4a): klasy ql-* (filtrowane po wartości) + wrapper embedu YouTube.
SANITIZER_VERSION = 2

ALLOWED_TAGS = [
    "p", "h2", "h3", "h4",
    "strong", "em", "u", "s",
    "a", "ul", "ol", "li",
    "blockquote", "code", "pre",
    "img", "br", "hr",
    "span", "div",
    "table", "thead", "tbody", "tr", "th", "td", "caption",
    # UWAGA: `iframe` celowo NIE jest tu wymieniony i nie może zostać dodany.
    # Embed YouTube generuje serwer z zwalidowanego URL-a (app/utils/embeds.py),
    # nie przyjmujemy gotowego <iframe> od klienta. Patrz plan, sekcja 7.
]

ALLOWED_ATTRIBUTES = {
    "a": ["href", "title", "class"],
    "img": ["src", "alt", "class"],
    "th": ["colspan", "rowspan", "class"],
    "td": ["colspan", "rowspan", "class"],
    "p": ["class"],
    "span": ["class"],
    # data-youtube-id to placeholder embedu; jego wartość jest walidowana
    # wzorcem w DataAttributeFilter, a na iframe zamienia go dopiero
    # render_embeds() przy wyświetlaniu (app/utils/embeds.py).
    "div": ["class", "data-youtube-id"],
    "h2": ["class"],
    "h3": ["class"],
    "h4": ["class"],
    "ul": ["class"],
    "ol": ["class"],
    "li": ["class"],
    "blockquote": ["class"],
    "pre": ["class"],
    "table": ["class"],
}

ALLOWED_PROTOCOLS = ["http", "https", "mailto"]

# Zamknięty zbiór klas, które generuje edytor Quill. Wszystko poza tym
# wzorcem jest wycinane — `class` NIE jest wolnym atrybutem, bo pozwoliłby
# wstrzyknąć dowolną klasę z naszego CSS-a i podszyć się pod element
# interfejsu (plan, sekcja 7).
_ALLOWED_CLASS_RE = re.compile(r"^ql-(?:align-(?:center|right|justify)|indent-[1-8]|syntax)$")

# Klasy wrapperów, które generuje serwer (embed YouTube, scroll tabeli).
# Dopuszczone, bo trafiają do treści z naszego kodu, nie od użytkownika —
# ale i tak przechodzą przez ten sam filtr, żeby nie robić wyjątku w regule.
_SERVER_CLASSES = frozenset({"embed-responsive", "table-wrapper"})


def _class_allowed(css_class):
    return bool(_ALLOWED_CLASS_RE.match(css_class)) or css_class in _SERVER_CLASSES


# ID filmu YouTube w placeholderze embedu — dokładnie 11 znaków
# z bezpiecznego alfabetu, tak jak waliduje to app/utils/embeds.py.
_YOUTUBE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


class QuillClassFilter(Filter):
    """Przepisuje `class` i `data-youtube-id`, filtrując je po wartości.

    Konieczne, bo callable w `bleach.clean(attributes=...)` dostaje całą
    wartość atrybutu naraz i może ją tylko przyjąć albo odrzucić w całości —
    `class="ql-align-center evil"` przeszłoby z doklejoną złośliwą klasą.
    Ten filtr działa na poziomie tokenów, więc potrafi wyciąć pojedyncze.
    """

    def __iter__(self):
        for token in Filter.__iter__(self):
            if token["type"] in ("StartTag", "EmptyTag") and token.get("data"):
                self._filter_attributes(token)
            yield token

    @staticmethod
    def _filter_attributes(token):
        for (namespace, name), value in list(token["data"].items()):
            if name == "class":
                kept = [c for c in value.split() if _class_allowed(c)]
                if kept:
                    token["data"][(namespace, name)] = " ".join(kept)
                else:
                    del token["data"][(namespace, name)]
            elif name == "data-youtube-id" and not _YOUTUBE_ID_RE.match(value):
                del token["data"][(namespace, name)]


_cleaner = Cleaner(
    tags=set(ALLOWED_TAGS),
    attributes=ALLOWED_ATTRIBUTES,
    protocols=ALLOWED_PROTOCOLS,
    filters=[QuillClassFilter],
    strip=True,
)


def sanitize_html(raw_html):
    """Sanityzuje HTML z edytora przed zapisem do body_html.

    Jedyne wejście do treści renderowanej przez `| safe`. Kolejność zapisu:
    body_source najpierw (bez zmian), potem body_html = sanitize_html(...).
    """
    return _cleaner.clean(raw_html or "")
