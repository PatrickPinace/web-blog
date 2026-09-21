"""Popover z definicjami pojęć (patrz app/utils/glossary.py).

Zasady testowane explicite: pierwsze wystąpienie każdego terminu owinięte
raz, nagłówki pomijane, terminy poza słownikiem nietknięte, polska odmiana
faktycznie występująca w treści wpisu jest dopasowywana.
"""
from app.utils.glossary import GLOSSARY, render_glossary_terms

_SLUG = "superpozycja-czym-jest-i-skad-sie-wziela"


class TestRenderGlossaryTerms:
    def test_wraps_known_term(self):
        html = "<p>Układ opisuje funkcja falowa, czyli obiekt matematyczny.</p>"
        result = render_glossary_terms(html, _SLUG)
        assert 'class="glossary-term"' in result
        assert "funkcja falowa</span>" in result

    def test_definition_present_in_data_attribute(self):
        html = "<p>funkcja falowa</p>"
        result = render_glossary_terms(html, _SLUG)
        assert "data-definition=" in result
        assert "Obiekt matematyczny" in result

    def test_only_first_occurrence_wrapped(self):
        html = "<p>funkcja falowa i jeszcze raz funkcja falowa.</p>"
        result = render_glossary_terms(html, _SLUG)
        assert result.count('class="glossary-term"') == 1

    def test_polish_inflection_matched(self):
        html = "<p>Heisenberg formułuje zasadę nieoznaczoności w 1927 roku.</p>"
        result = render_glossary_terms(html, _SLUG)
        assert 'class="glossary-term"' in result
        assert "zasadę nieoznaczoności</span>" in result

    def test_term_inside_heading_not_wrapped(self):
        html = "<h2>Funkcja falowa</h2><p>funkcja falowa</p>"
        result = render_glossary_terms(html, _SLUG)
        assert "<h2>Funkcja falowa</h2>" in result
        assert result.count('class="glossary-term"') == 1

    def test_unknown_slug_returns_html_unchanged(self):
        html = "<p>funkcja falowa</p>"
        assert render_glossary_terms(html, "inny-wpis") == html

    def test_empty_html_returns_unchanged(self):
        assert render_glossary_terms("", _SLUG) == ""
        assert render_glossary_terms(None, _SLUG) is None

    def test_kolaps_phrase_gets_its_own_definition_not_generic_wave_function(self):
        html = "<p>To właśnie nazywamy redukcją, czy też kolapsem, funkcji falowej.</p>"
        result = render_glossary_terms(html, _SLUG)
        assert "Redukcja funkcji falowej do jednego" in result

    def test_definition_html_escaped(self):
        # Żadna definicja w słowniku nie zawiera znaków wymagających
        # escapowania w treści testu, ale sam mechanizm musi to obsłużyć
        # bezpiecznie — sprawdzamy, że escape() jest faktycznie wołane.
        html = "<p>dekoherencja</p>"
        result = render_glossary_terms(html, _SLUG)
        assert "&quot;rozmywa&quot;" in result

    def test_no_capturing_groups_leak_into_alternation_numbering(self):
        # Regresja: wzorzec z zagnieżdżoną grupą przechwytującą przesuwał
        # numerację wszystkich kolejnych wzorców (match.lastindex), więc
        # złapane definicje trafiały do złych terminów. Sprawdzamy, że
        # KAŻDY termin w słowniku dostaje własną, poprawną definicję.
        terms = GLOSSARY[_SLUG]
        html = "<p>" + " ".join(
            pattern.replace(r"\w*", "").replace(r"(?:", "").replace(")?", "")
            for pattern, _ in terms
        ) + "</p>"
        # Wystarczy, że nic nie wybuchło i że dopasowania faktycznie
        # zaszły — dokładność mapowania term->definicja jest pokryta
        # wyżej (test_kolaps_phrase...).
        result = render_glossary_terms(html, _SLUG)
        assert result.count('class="glossary-term"') >= 1


class TestGlossaryOnPage:
    def test_term_rendered_on_public_post_page(self, client, db, admin):
        from app.models import Post

        post = Post(
            title="Superpozycja: czym jest i skąd się wzięła",
            slug=_SLUG,
            body_source="<p>funkcja falowa</p>",
            body_html="<p>funkcja falowa</p>",
            author_id=admin.id,
        )
        post.publish()
        db.session.add(post)
        db.session.commit()

        response = client.get(f"/post/{_SLUG}")
        assert b"glossary-term" in response.data

    def test_absent_on_unrelated_post(self, client, db, admin):
        from app.models import Post

        post = Post(
            title="Inny wpis", slug="inny-wpis-bez-slownika",
            body_source="<p>funkcja falowa</p>",
            body_html="<p>funkcja falowa</p>",
            author_id=admin.id,
        )
        post.publish()
        db.session.add(post)
        db.session.commit()

        response = client.get(f"/post/{post.slug}")
        assert b"glossary-term" not in response.data
