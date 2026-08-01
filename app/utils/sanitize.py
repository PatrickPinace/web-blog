import bleach

# Wersja reguł sanitizera. Podbij przy KAŻDEJ zmianie whitelisty poniżej —
# pozwala znaleźć wpisy do przeliczenia przez `flask resanitize`
# (plan, sekcja 7 i procedura w sekcji 7 "Procedura zmiany whitelisty").
#
# v1 (etap 4): whitelist bazowa, bez klas Quilla i bez embedów.
# Rozszerzenie o ql-* i embed YouTube — etap 4a.
SANITIZER_VERSION = 1

ALLOWED_TAGS = [
    "p", "h2", "h3", "h4",
    "strong", "em", "u", "s",
    "a", "ul", "ol", "li",
    "blockquote", "code", "pre",
    "img", "br", "hr",
    "table", "thead", "tbody", "tr", "th", "td", "caption",
]

ALLOWED_ATTRIBUTES = {
    "a": ["href", "title"],
    "img": ["src", "alt"],
    "th": ["colspan", "rowspan"],
    "td": ["colspan", "rowspan"],
}

ALLOWED_PROTOCOLS = ["http", "https", "mailto"]


def sanitize_html(raw_html):
    """Sanityzuje HTML z edytora przed zapisem do body_html.

    Nigdy nie wywołuj na treści, która trafi bezpośrednio do `| safe`
    bez przejścia przez tę funkcję. Kolejność zapisu: body_source najpierw
    (bez zmian), potem body_html = sanitize_html(body_source).
    """
    return bleach.clean(
        raw_html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )
