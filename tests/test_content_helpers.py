"""Helpery liczone z treści: czas czytania i kotwice nagłówków.

`add_heading_ids` wstawia atrybut do HTML tuż przed renderowaniem, więc
testujemy go też pod kątem tego, czego wstawić NIE wolno.
"""

from datetime import timedelta

from app.models import utcnow
from app.utils.content import (
    add_heading_ids,
    add_image_loading_attrs,
    first_image_url,
    pluralize_pl,
    read_time,
    strip_tags,
    time_ago_pl,
    was_updated_after_publish,
    wrap_tables,
)


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


class TestTimeAgoPl:
    def test_just_now_for_recent(self):
        assert time_ago_pl(utcnow()) == "przed chwilą"

    def test_days_ago(self):
        dt = utcnow() - timedelta(days=3)
        assert time_ago_pl(dt) == "3 dni temu"

    def test_one_day_uses_singular(self):
        dt = utcnow() - timedelta(days=1, hours=1)
        assert time_ago_pl(dt) == "1 dzień temu"

    def test_months_ago(self):
        dt = utcnow() - timedelta(days=65)
        assert time_ago_pl(dt) == "2 miesiące temu"

    def test_years_ago(self):
        dt = utcnow() - timedelta(days=400)
        assert time_ago_pl(dt) == "1 rok temu"

    def test_naive_datetime_treated_as_utc(self):
        dt = (utcnow() - timedelta(days=5)).replace(tzinfo=None)
        assert time_ago_pl(dt) == "5 dni temu"


class _FakePost:
    def __init__(self, published_at, updated_at):
        self.published_at = published_at
        self.updated_at = updated_at


class TestWasUpdatedAfterPublish:
    def test_false_when_never_published(self):
        assert was_updated_after_publish(_FakePost(None, utcnow())) is False

    def test_false_for_microsecond_gap_between_the_two_utcnow_calls(self):
        published = utcnow()
        updated = published + timedelta(microseconds=500)
        assert was_updated_after_publish(_FakePost(published, updated)) is False

    def test_true_for_real_edit_later(self):
        published = utcnow() - timedelta(days=3)
        updated = utcnow()
        assert was_updated_after_publish(_FakePost(published, updated)) is True

    def test_handles_naive_datetimes_from_sqlite(self):
        published = (utcnow() - timedelta(days=3)).replace(tzinfo=None)
        updated = utcnow().replace(tzinfo=None)
        assert was_updated_after_publish(_FakePost(published, updated)) is True


class TestAddImageLoadingAttrs:
    def test_adds_loading_and_decoding(self):
        html = '<img src="a.jpg" alt="x">'
        result = add_image_loading_attrs(html)
        assert 'loading="lazy"' in result
        assert 'decoding="async"' in result
        assert 'src="a.jpg"' in result

    def test_preserves_self_closing_slash(self):
        html = '<img src="a.jpg"/>'
        result = add_image_loading_attrs(html)
        assert result.endswith('loading="lazy" decoding="async"/>')

    def test_multiple_images_all_get_attrs(self):
        html = '<img src="a.jpg"><p>tekst</p><img src="b.jpg">'
        result = add_image_loading_attrs(html)
        assert result.count('loading="lazy"') == 2

    def test_empty_or_none_returns_unchanged(self):
        assert add_image_loading_attrs("") == ""
        assert add_image_loading_attrs(None) is None

    def test_no_image_returns_unchanged(self):
        html = "<p>bez obrazka</p>"
        assert add_image_loading_attrs(html) == html


class TestFirstImageUrl:
    def test_finds_src_of_first_image(self):
        html = '<p>tekst</p><img src="https://example.com/a.jpg" alt=""><img src="https://example.com/b.jpg">'
        assert first_image_url(html) == "https://example.com/a.jpg"

    def test_no_image_returns_none(self):
        assert first_image_url("<p>bez obrazka</p>") is None

    def test_empty_or_none_returns_none(self):
        assert first_image_url("") is None
        assert first_image_url(None) is None


class TestPluralizePl:
    def _forms(self, n):
        return pluralize_pl(n, "wpis", "wpisy", "wpisów")

    def test_one_is_singular(self):
        assert self._forms(1) == "wpis"

    def test_two_to_four_is_few(self):
        assert [self._forms(n) for n in (2, 3, 4)] == ["wpisy"] * 3

    def test_zero_and_five_plus_is_many(self):
        assert self._forms(0) == "wpisów"
        assert [self._forms(n) for n in (5, 6, 10, 11)] == ["wpisów"] * 4

    def test_eleven_to_fourteen_is_many_not_few(self):
        # Wyjątek od "ostatnia cyfra 2-4 => few": 12, 13, 14 mimo cyfry
        # 2/3/4 na końcu idą do "many", tak samo jak 112, 113, 114.
        assert [self._forms(n) for n in (12, 13, 14, 112, 113, 114)] == ["wpisów"] * 6

    def test_twenty_two_is_few_again(self):
        assert [self._forms(n) for n in (22, 23, 24, 122)] == ["wpisy"] * 4

    def test_twenty_one_is_many_not_singular(self):
        # W polskim "21 wpisów", NIE "21 wpis" - tylko dosłowne 1 jest liczbą
        # pojedynczą, 21/31/... mimo końcówki 1 idą do formy "many".
        assert self._forms(21) == "wpisów"


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


def test_wrap_tables_keeps_table_inside_local_scroll_container():
    html = wrap_tables("<p>Wstęp</p><table><tr><td>x</td></tr></table>")
    assert html == '<p>Wstęp</p><div class="table-wrapper"><table><tr><td>x</td></tr></table></div>'
