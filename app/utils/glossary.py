"""Popover z definicjami pojęć w treści wpisu.

Zamiast placeholderów w edytorze (jak embed YouTube), słownik jest osobnym,
deklaratywnym źródłem: definicje żyją tutaj, nie w `body_source`. Dzięki temu
dodanie/poprawienie definicji nie wymaga edycji wpisu przez panel i nie
dotyka sanitizera — `render_glossary_terms()` tylko owija już zsanityzowany
`body_html` w locie, tym samym wzorcem co `render_embeds`/`add_heading_ids`.

Każdy termin jest owijany TYLKO przy pierwszym wystąpieniu w treści (poza
nagłówkami) — dalsze powtórzenia tego samego słowa nie potrzebują tooltipa
drugi raz, a wielokrotne podkreślenia tego samego terminu w jednym akapicie
rozpraszałyby bardziej niż pomagały.
"""
import re
from html import escape

# slug wpisu -> lista (wzorzec_regex, definicja). Wzorzec dopasowuje formę
# FAKTYCZNIE użytą w treści (polska odmiana: "zasadę nieoznaczoności" w
# tekście, nie mianownikowe "zasada") — sprawdzone empirycznie na body_html
# tego wpisu, nie zgadywane. `\w*` na końcu rdzenia łapie dopełnienie/
# odmianę bez podawania każdej formy osobno.
#
# WAŻNE: żadna grupa WEWNĄTRZ wzorca nie może przechwytywać — użyj (?:...),
# nigdy (...) — bo _terms_pattern() liczy numer dopasowanej alternatywy przez
# match.lastindex, a każda dodatkowa przechwytująca grupa przesuwa numerację
# WSZYSTKICH kolejnych wzorców w liście (złapane testem, nie na oko).
GLOSSARY = {
    "superpozycja-czym-jest-i-skad-sie-wziela": [
        (
            r"zasad\w* nieoznaczonoś\w*",
            "Sformułowana przez Heisenberga w 1927 roku: nie można "
            "jednocześnie z dowolną dokładnością znać pędu i położenia "
            "cząstki. To nie ograniczenie pomiaru, lecz fundamentalna "
            "własność przyrody — lepszy sprzęt by tu nie pomógł.",
        ),
        (
            r"(?:kolaps\w*|redukcj\w*)(?:,?\s+czy\s+też\s+kolapsem,)?\s+funkcj\w* falow\w*",
            "Redukcja funkcji falowej do jednego, konkretnego stanu w "
            "momencie pomiaru. Przed pomiarem układ opisuje superpozycja "
            "wielu możliwych wyników; po pomiarze zostaje tylko jeden.",
        ),
        (
            r"funkcj\w* falow\w*",
            "Obiekt matematyczny opisujący układ kwantowy — zawiera "
            "wszystkie możliwe wyniki pomiaru, każdy z przypisanym "
            "prawdopodobieństwem. Nie jest falą fizyczną (jak fala na "
            "wodzie), tylko falą prawdopodobieństwa.",
        ),
        (
            r"dekoherencj\w*",
            "Proces, w którym oddziaływanie układu kwantowego z otoczeniem "
            "\"rozmywa\" fazy między stanami superpozycji, czyniąc ją "
            "praktycznie niewidoczną w skali makroskopowej. Tłumaczy, "
            "dlaczego nie widzimy kotów w superpozycji, bez rozstrzygania "
            "samego problemu pomiaru.",
        ),
        (
            r"kubit\w*",
            "Kwantowy bit — jednostka informacji w komputerze kwantowym. "
            "W przeciwieństwie do klasycznego bitu (0 albo 1) może "
            "znajdować się w superpozycji obu wartości jednocześnie.",
        ),
    ],
}


def _terms_pattern(terms):
    # Każdy wzorzec w swojej grupie przechwytującej — po dopasowaniu
    # match.lastindex mówi, KTÓRY wzorzec (a więc która definicja) wygrał,
    # zamiast zgadywać to z samego dopasowanego tekstu (zawodne przy odmianie).
    #
    # Dłuższe/bardziej specyficzne wzorce muszą iść pierwsze w alternacji —
    # re.search próbuje je po kolei i bierze pierwszy, który się dopasuje
    # w danej pozycji, więc "kolaps funkcji falowej" musi wygrać z samym
    # "funkcja falowa", inaczej ten drugi "pożre" wspólny ogon frazy.
    patterns = [f"({pattern})" for pattern, _ in terms]
    return re.compile(r"\b(?:" + "|".join(patterns) + r")\b", re.IGNORECASE)


def render_glossary_terms(html, slug):
    """Owija pierwsze wystąpienie każdego zdefiniowanego terminu w treści.

    Pomija nagłówki (h2/h3/h4) — termin w tytule sekcji nie potrzebuje
    tooltipa, a psowałby wygląd nagłówka. Działa na już zsanityzowanym
    body_html, tuż przed wyświetleniem.
    """
    terms = GLOSSARY.get(slug)
    if not html or not terms:
        return html

    pattern = _terms_pattern(terms)
    definitions = [definition for _, definition in terms]
    seen = set()

    # Nagłówki wyjęte na czas zamiany, żeby termin w <h2> nie dostał
    # tooltipa — re.split z grupą zachowuje separatory w wyniku.
    parts = re.split(r"(<h[234][^>]*>.*?</h[234]>)", html, flags=re.IGNORECASE | re.DOTALL)

    def _replace(match):
        word = match.group(0)
        # lastindex to numer grupy, która dopasowała (1-indexed) — mówi,
        # KTÓRY z wzorców w GLOSSARY wygrał, więc która definicja pasuje.
        term_index = match.lastindex - 1
        if term_index in seen:
            return word
        seen.add(term_index)
        definition = escape(definitions[term_index])
        return (
            f'<span class="glossary-term" tabindex="0" data-definition="{definition}">'
            f"{word}</span>"
        )

    for i, part in enumerate(parts):
        if i % 2 == 0:  # parts na indeksach parzystych to tekst, nieparzystych — nagłówki
            parts[i] = pattern.sub(_replace, part)

    return "".join(parts)
