"""Meta OG/Twitter na stronie wpisu — karta społecznościowa przy udostępnianiu
(patrz app/templates/base.html: blocki og_*, app/public/routes.py: post_detail).
"""
from app.models import Post


def _publish(db, admin, title, slug, body_html="<p>tresc</p>", excerpt=None):
    post = Post(
        title=title, slug=slug, excerpt=excerpt,
        body_source=body_html, body_html=body_html, author_id=admin.id,
    )
    post.publish()
    db.session.add(post)
    db.session.commit()
    return post


class TestOgTags:
    def test_og_title_matches_post_title(self, client, db, admin):
        post = _publish(db, admin, "Tytuł wpisu", "tytul-wpisu")
        response = client.get(f"/post/{post.slug}")
        assert b'property="og:title" content="Tytu\xc5\x82 wpisu"' in response.data

    def test_og_type_is_article(self, client, db, admin):
        post = _publish(db, admin, "Wpis", "wpis")
        response = client.get(f"/post/{post.slug}")
        assert b'property="og:type" content="article"' in response.data

    def test_og_url_points_to_post(self, client, db, admin):
        post = _publish(db, admin, "Wpis", "wpis-url")
        response = client.get(f"/post/{post.slug}")
        assert b"/post/wpis-url" in response.data

    def test_no_image_in_body_falls_back_to_summary_card(self, client, db, admin):
        post = _publish(db, admin, "Bez obrazka", "bez-obrazka")
        response = client.get(f"/post/{post.slug}")
        assert b'og:image' not in response.data
        assert b'name="twitter:card" content="summary"' in response.data

    def test_image_in_body_becomes_og_image(self, client, db, admin):
        post = _publish(
            db, admin, "Z obrazkiem", "z-obrazkiem",
            body_html='<p>tekst</p><img src="https://example.com/cover.jpg" alt="">',
        )
        response = client.get(f"/post/{post.slug}")
        assert b'property="og:image" content="https://example.com/cover.jpg"' in response.data
        assert b'name="twitter:card" content="summary_large_image"' in response.data

    def test_index_has_website_og_type_not_article(self, client):
        response = client.get("/")
        assert b'property="og:type" content="website"' in response.data
