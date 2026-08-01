"""Testy sanityzacji HTML z edytora.

Uruchamiane osobno: `pytest tests/security`. OBOWIĄZKOWE po każdej zmianie
whitelisty w app/utils/sanitize.py (plan, sekcja 7).
"""

import pytest

from app.utils.sanitize import sanitize_html


@pytest.mark.parametrize(
    "payload",
    [
        "<script>alert(1)</script>",
        "<p>tekst</p><script>alert(1)</script>",
        "<SCRIPT>alert(1)</SCRIPT>",
        "<scr<script>ipt>alert(1)</script>",
        "<img src=x onerror=alert(1)>",
        "<p onclick='alert(1)'>klik</p>",
        "<p onmouseover=alert(1)>hover</p>",
        "<a href='javascript:alert(1)'>link</a>",
        "<a href='JaVaScRiPt:alert(1)'>link</a>",
        "<a href='data:text/html,<script>alert(1)</script>'>link</a>",
        "<iframe src='https://evil.tld'></iframe>",
        "<object data='evil.swf'></object>",
        "<embed src='evil.swf'>",
        "<form action='/steal'><input name=x></form>",
        "<style>body{display:none}</style>",
        "<link rel=stylesheet href='evil.css'>",
        "<meta http-equiv=refresh content='0;url=evil'>",
        "<base href='https://evil.tld/'>",
        "<svg onload=alert(1)>",
        "<math><mtext><script>alert(1)</script></mtext></math>",
    ],
)
def test_dangerous_payload_is_neutralised(payload):
    result = sanitize_html(payload)

    lowered = result.lower()
    assert "<script" not in lowered
    assert "<iframe" not in lowered
    assert "<object" not in lowered
    assert "<embed" not in lowered
    assert "<form" not in lowered
    assert "<style" not in lowered
    assert "<base" not in lowered
    assert "onerror" not in lowered
    assert "onclick" not in lowered
    assert "onload" not in lowered
    assert "onmouseover" not in lowered
    assert "javascript:" not in lowered.replace("&#", "")


def test_iframe_is_never_allowed_even_for_youtube():
    """iframe nie wchodzi na whitelistę nawet dla zaufanej domeny.

    Embed generuje serwer (app/utils/embeds.py) — nie przyjmujemy gotowego
    znacznika od użytkownika.
    """
    payload = '<iframe src="https://www.youtube.com/embed/dQw4w9WgXcQ"></iframe>'
    assert "<iframe" not in sanitize_html(payload).lower()


def test_style_attribute_is_stripped():
    result = sanitize_html('<p style="position:fixed;top:0">x</p>')
    assert "style" not in result.lower()


class TestClassWhitelist:
    """Atrybut `class` przechodzi filtrowanie PO WARTOŚCI, nie w całości."""

    def test_quill_classes_survive(self):
        for css_class in [
            "ql-align-center",
            "ql-align-right",
            "ql-align-justify",
            "ql-indent-1",
            "ql-indent-8",
            "ql-syntax",
        ]:
            result = sanitize_html(f'<p class="{css_class}">x</p>')
            assert css_class in result, f"{css_class} powinna przetrwać"

    def test_foreign_class_is_stripped(self):
        result = sanitize_html('<p class="admin-panel-nav">x</p>')
        assert "admin-panel-nav" not in result
        assert "class" not in result

    def test_foreign_class_stripped_when_mixed_with_allowed(self):
        """Najważniejszy przypadek: doklejenie złośliwej klasy do dozwolonej."""
        result = sanitize_html('<p class="ql-align-center admin-panel-nav">x</p>')
        assert "ql-align-center" in result
        assert "admin-panel-nav" not in result

    def test_class_resembling_quill_is_rejected(self):
        for css_class in ["ql-evil", "ql-align-evil", "ql-indent-99", "qlx-align-center"]:
            result = sanitize_html(f'<p class="{css_class}">x</p>')
            assert css_class not in result, f"{css_class} nie powinna przejść"


def test_allowed_formatting_survives():
    payload = (
        "<h2>Nagłówek</h2><p><strong>pogrubienie</strong> i <em>kursywa</em></p>"
        "<ul><li>punkt</li></ul><ol><li>numer</li></ol>"
        "<blockquote>cytat</blockquote>"
        '<a href="https://example.com" title="t">link</a>'
    )
    result = sanitize_html(payload)
    for fragment in ["<h2>", "<strong>", "<em>", "<ul>", "<ol>", "<blockquote>", "href"]:
        assert fragment in result


def test_table_markup_survives():
    payload = (
        "<table><caption>Cennik</caption><thead><tr><th>A</th></tr></thead>"
        '<tbody><tr><td colspan="2">B</td></tr></tbody></table>'
    )
    result = sanitize_html(payload)
    for fragment in ["<table>", "<thead>", "<tbody>", "<th>", "<td", "colspan"]:
        assert fragment in result


class TestEmbedPlaceholder:
    """Placeholder embedu musi przetrwać sanityzację, ale bez iframe'a."""

    def test_placeholder_survives(self):
        from app.utils.embeds import build_youtube_placeholder

        placeholder = build_youtube_placeholder("https://youtu.be/dQw4w9WgXcQ")
        result = sanitize_html(placeholder)
        assert 'data-youtube-id="dQw4w9WgXcQ"' in result
        assert "<iframe" not in result.lower()

    def test_forged_video_id_is_stripped(self):
        """Ręcznie spreparowane ID nie może przejść przez sanitizer."""
        for forged in [
            '"><script>alert(1)</script>',
            "../../etc/passwd",
            "short",
            "way-too-long-video-id",
        ]:
            result = sanitize_html(f'<div data-youtube-id="{forged}"></div>')
            assert "data-youtube-id" not in result, f"{forged} nie powinno przejść"

    def test_rendered_embed_only_targets_youtube_nocookie(self):
        from app.utils.embeds import build_youtube_placeholder, render_embeds

        placeholder = build_youtube_placeholder("https://youtu.be/dQw4w9WgXcQ")
        rendered = render_embeds(sanitize_html(placeholder))
        assert "<iframe" in rendered
        assert "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ" in rendered

    def test_render_embeds_ignores_foreign_markup(self):
        """render_embeds nie może być furtką na wstrzyknięcie ramki."""
        from app.utils.embeds import render_embeds

        hostile = '<div class="embed-responsive" data-youtube-id="../../evil"></div>'
        assert "<iframe" not in render_embeds(hostile).lower()
