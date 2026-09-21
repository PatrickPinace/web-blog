"""Round-trip edytora: zapis -> odczyt -> ponowny zapis nie może gubić
formatowania (plan, sekcja 8, "Test round-trip edytora").

Formularz edycji wypełnia się z `post.body_source` (nie z body_html), więc
symulujemy dokładnie tę ścieżkę: to, co wraca z serwera jako wartość pola
edytora, wysyłamy ponownie jako kolejny zapis.
"""

from app.models import Post


def _create(auth_client, body_source, **extra):
    data = {
        "title": "Wpis round-trip", "excerpt": "e", "tags": "",
        "status": "draft", "body_source": body_source,
    }
    data.update(extra)
    auth_client.post("/admin/post/new", data=data)
    return Post.query.filter_by(title="Wpis round-trip").first()


def _resave(auth_client, post, body_source):
    auth_client.post(
        f"/admin/post/{post.id}/edit",
        data={
            "title": "Wpis round-trip", "excerpt": "e", "tags": "",
            "status": "draft", "body_source": body_source,
        },
    )


def test_alignment_class_survives_roundtrip(auth_client, db):
    post = _create(auth_client, '<p class="ql-align-center">wysrodkowany</p>')
    assert "ql-align-center" in post.body_html

    _resave(auth_client, post, post.body_source)
    db.session.refresh(post)
    assert "ql-align-center" in post.body_html


def test_indent_class_survives_roundtrip(auth_client, db):
    post = _create(auth_client, '<p class="ql-indent-2">wciety</p>')
    _resave(auth_client, post, post.body_source)
    db.session.refresh(post)
    assert "ql-indent-2" in post.body_html


def test_heading_and_code_block_survive_roundtrip(auth_client, db):
    body = '<h2>Nagłówek redakcyjny</h2><pre class="ql-syntax">print("kod")</pre>'
    post = _create(auth_client, body)

    _resave(auth_client, post, post.body_source)
    db.session.refresh(post)

    assert "<h2>Nagłówek redakcyjny</h2>" in post.body_html
    assert 'class="ql-syntax"' in post.body_html
    assert 'print("kod")' in post.body_html


def test_table_survives_roundtrip(auth_client, db):
    body = "<table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table>"
    post = _create(auth_client, body)
    for fragment in ["<table>", "<th>", "<td"]:
        assert fragment in post.body_html

    _resave(auth_client, post, post.body_source)
    db.session.refresh(post)
    for fragment in ["<table>", "<th>", "<td"]:
        assert fragment in post.body_html


def test_youtube_embed_placeholder_survives_roundtrip(auth_client, db):
    post = _create(
        auth_client,
        '<div class="embed-responsive" data-youtube-id="dQw4w9WgXcQ"></div>',
    )
    assert 'data-youtube-id="dQw4w9WgXcQ"' in post.body_html
    assert "<iframe" not in post.body_html

    _resave(auth_client, post, post.body_source)
    db.session.refresh(post)
    assert 'data-youtube-id="dQw4w9WgXcQ"' in post.body_html


def test_mixed_formatting_survives_two_roundtrips(auth_client, db):
    body = (
        '<h2 class="ql-align-center">Tytul</h2>'
        '<p class="ql-indent-1">Wciety akapit z <strong>pogrubieniem</strong></p>'
        "<blockquote>Cytat</blockquote>"
        "<ul><li>Punkt</li></ul>"
        '<div class="embed-responsive" data-youtube-id="dQw4w9WgXcQ"></div>'
    )
    post = _create(auth_client, body)
    first_pass = post.body_html

    _resave(auth_client, post, post.body_source)
    db.session.refresh(post)
    second_pass = post.body_html

    # Dwa kolejne przebiegi sanityzacji tego samego source'a muszą dać
    # identyczny wynik — to jest sedno "round-trip nie gubi formatowania".
    assert first_pass == second_pass

    for fragment in [
        "ql-align-center", "ql-indent-1", "<strong>", "<blockquote>",
        "<ul>", "<li>", 'data-youtube-id="dQw4w9WgXcQ"',
    ]:
        assert fragment in second_pass


def test_gallery_figure_and_figcaption_survive_roundtrip(auth_client, db):
    # Dodane w sanitizer_version 3 — CSS na .gallery figure/figcaption
    # istniał od wpięcia designu, ale sanitizer wycinał oba tagi
    # (znalezione przy pisaniu pierwszego case study z galerią).
    body = (
        '<div class="gallery">'
        "<figure><img src=\"https://res.cloudinary.com/demo/x.jpg\" alt=\"a\">"
        "<figcaption>Podpis zdjęcia</figcaption></figure>"
        "</div>"
    )
    post = _create(auth_client, body)
    assert "<figure>" in post.body_html
    assert "<figcaption>" in post.body_html

    _resave(auth_client, post, post.body_source)
    db.session.refresh(post)
    assert "<figure>" in post.body_html
    assert "<figcaption>" in post.body_html
