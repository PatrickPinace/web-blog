"""Helpery liczone z treści: czas czytania i kotwice nagłówków.

`add_heading_ids` wstawia atrybut do HTML tuż przed renderowaniem, więc
testujemy go też pod kątem tego, czego wstawić NIE wolno.
"""

from app.utils.content import add_heading_ids, read_time, strip_tags


class TestReadTime:
    def test_empty_body_is_one_minute_not_zero(self):
        assert read_time("") == 1
        assert read_time("<p></p>") == 1

    def test_rounds_up_to_full_minutes(self):
        assert read_time("<p>" + "slowo " * 200 + "</p>") == 1
        assert read_time("<p>" + "slowo " * 201 + "</p>") == 2

    def test_markup_is_not_counted_as_words(self):
        plain = read_time("<p>" + "slowo " * 400 + "</p>")
        marked = read_time("<p><strong>" + "slowo </strong><em>" * 400 + "</em></p>")
        assert plain == marked


class TestHeadingIds:
    def test_adds_ids_and_returns_toc(self):
        html, headings = add_heading_ids("<h2>Pierwsza</h2><h3>Druga</h3>")
        assert 'id="pierwsza"' in html
        assert [h["id"] for h in headings] == ["pierwsza", "druga"]
        assert [h["level"] for h in headings] == ["h2", "h3"]

    def test_polish_characters_are_transliterated(self):
        html, headings = add_heading_ids("<h2>Zażółć gęślą jaźń</h2>")
        assert headings[0]["id"] == "zazolc-gesla-jazn"
        assert "Zażółć gęślą jaźń" in html  # tekst zostaje nietknięty

    def test_duplicate_titles_get_unique_ids(self):
        _, headings = add_heading_ids("<h2>Ten sam</h2><h2>Ten sam</h2>")
        assert [h["id"] for h in headings] == ["ten-sam", "ten-sam-2"]

    def test_h1_is_skipped(self):
        # H1 to tytuł wpisu w nagłówku strony — w spisie treści byłby duplikatem.
        html, headings = add_heading_ids("<h1>Tytul</h1><h2>Sekcja</h2>")
        assert headings == [{"id": "sekcja", "text": "Sekcja", "level": "h2"}]
        assert "<h1>Tytul</h1>" in html

    def test_existing_id_is_not_overwritten(self):
        html, headings = add_heading_ids('<h2 id="moje">Ma id</h2>')
        assert 'id="moje"' in html
        assert headings == []

    def test_existing_attributes_are_preserved(self):
        html, _ = add_heading_ids('<h2 class="ql-align-center">Z klasa</h2>')
        assert 'class="ql-align-center"' in html
        assert 'id="z-klasa"' in html

    def test_empty_heading_gets_no_id(self):
        html, headings = add_heading_ids("<h2></h2><h2>   </h2>")
        assert "id=" not in html
        assert headings == []

    def test_id_cannot_break_out_of_the_attribute(self):
        # Cudzysłów i spacja w tekście nagłówka nie mogą trafić do atrybutu —
        # inaczej dałoby się dokleić własny atrybut do tagu.
        html, headings = add_heading_ids('<h2>a" onload="alert(1)</h2>')
        assert 'onload=' not in html.replace('a" onload="alert(1)', "")
        assert headings[0]["id"] == "a-onload-alert-1"

    def test_id_alphabet_is_restricted(self):
        _, headings = add_heading_ids("<h2>A<>&'\"/\\ B</h2>")
        assert all(c.isalnum() or c == "-" for c in headings[0]["id"])


def test_strip_tags_collapses_whitespace():
    assert strip_tags("<p>a</p>\n<p>  b  </p>") == "a b"
