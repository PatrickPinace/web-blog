"""Sitemap i robots.txt: dostępność, treść, brak wycieku szkiców."""
from app.models import Post


def _publish(db, admin, title, slug):
    post = Post(
        title=title,
        slug=slug,
        body_source="<p>tresc</p>",
        body_html="<p>tresc</p>",
        author_id=admin.id,
    )
    post.publish()
    db.session.add(post)
    db.session.commit()
    return post


class TestSitemap:
    def test_returns_xml(self, client):
        response = client.get("/sitemap.xml")
        assert response.status_code == 200
        assert response.mimetype == "application/xml"

    def test_lists_published_post(self, client, db, admin):
        _publish(db, admin, "Opublikowany", "opublikowany")
        response = client.get("/sitemap.xml")
        assert b"/post/opublikowany" in response.data

    def test_includes_static_pages(self, client):
        response = client.get("/sitemap.xml")
        assert b"<loc>" in response.data
        for path in (b"/about", b"/tagi", b"/szukaj"):
            assert path in response.data


class TestRobots:
    def test_returns_text_and_disallows_admin(self, client):
        response = client.get("/robots.txt")
        assert response.status_code == 200
        assert response.mimetype == "text/plain"
        assert b"Disallow: /admin/" in response.data

    def test_points_to_sitemap(self, client):
        response = client.get("/robots.txt")
        assert b"Sitemap:" in response.data
        assert b"/sitemap.xml" in response.data
