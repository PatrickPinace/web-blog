"""Transliteracja polskich znaków na slug URL.

`ł` jest szczególnym przypadkiem: w przeciwieństwie do ą/ć/ę/ń/ó/ś/ź/ż nie
ma dekompozycji diakrytycznej w Unicode, więc naiwne NFKD + ascii-ignore
po prostu ją usuwa zamiast zamienić na "l" (znalezione na tytule
zawierającym "wzięła" -> slug "wzięa").
"""

from app.utils.slugify import slugify, unique_slug


class TestSlugify:
    def test_ascii_title_is_lowercased_and_hyphenated(self):
        assert slugify("Hello World") == "hello-world"

    def test_all_polish_diacritics_are_transliterated(self):
        assert slugify("Zażółć gęślą jaźń") == "zazolc-gesla-jazn"

    def test_l_with_stroke_is_not_silently_dropped(self):
        assert slugify("wzięła") == "wziela"
        assert "l" in slugify("Łódź")

    def test_uppercase_l_with_stroke(self):
        assert slugify("ŁÓDŹ") == "lodz"

    def test_punctuation_collapses_to_single_hyphen(self):
        assert slugify("Co, kiedy i jak?!") == "co-kiedy-i-jak"

    def test_empty_or_symbols_only_falls_back_to_default(self):
        assert slugify("") == "wpis"
        assert slugify("!!!???") == "wpis"


class TestUniqueSlug:
    def test_appends_counter_on_collision(self):
        taken = {"post", "post-2"}
        assert unique_slug("post", lambda s: s in taken) == "post-3"

    def test_returns_base_when_free(self):
        assert unique_slug("wolny", lambda s: False) == "wolny"
