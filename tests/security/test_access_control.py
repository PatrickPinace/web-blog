"""Kontrola dostępu: panel admina i widoczność szkiców.

Uruchamiane osobno: `pytest tests/security`.
"""

import pytest

from app.models import Post


def _make_post(db, admin, **overrides):
    fields = {
        "title": "Wpis",
        "slug": "wpis",
        "body_source": "<p>tresc</p>",
        "body_html": "<p>tresc</p>",
        "author_id": admin.id,
    }
    fields.update(overrides)
    post = Post(**fields)
    if fields.get("status") == Post.STATUS_PUBLISHED:
        post.publish()
    db.session.add(post)
    db.session.commit()
    return post


class TestAdminRequiresLogin:
    @pytest.mark.parametrize(
        "path",
        [
            "/admin/",
            "/admin/post/new",
            "/admin/post/1/edit",
            "/admin/post/1/preview",
            "/admin/labels",
            "/admin/tags",
        ],
    )
    def test_get_redirects_to_login(self, client, path):
        response = client.get(path)
        assert response.status_code == 302
        assert "/admin/login" in response.location

    @pytest.mark.parametrize(
        "path",
        [
            "/admin/post/1/delete",
            "/admin/post/1/toggle-status",
            "/admin/post/1/duplicate",
            "/admin/upload-image",
            "/admin/embed-youtube",
            "/admin/check-image-url",
            "/admin/logout",
            "/admin/labels/1/edit",
            "/admin/labels/1/delete",
            "/admin/tags/1/rename",
            "/admin/tags/1/delete",
            "/admin/tags/merge",
        ],
    )
    def test_post_requires_auth(self, client, path):
        response = client.post(path)
        assert response.status_code in (302, 401), f"{path} dostępne bez logowania"
        if response.status_code == 302:
            assert "/admin/login" in response.location


class TestDraftVisibility:
    def test_draft_not_listed(self, client, db, admin):
        _make_post(db, admin, title="Szkic", slug="szkic", status=Post.STATUS_DRAFT)
        response = client.get("/")
        assert b"Szkic" not in response.data

    def test_draft_direct_url_returns_404(self, client, db, admin):
        _make_post(db, admin, title="Szkic", slug="szkic", status=Post.STATUS_DRAFT)
        assert client.get("/post/szkic").status_code == 404

    def test_draft_absent_from_rss(self, client, db, admin):
        _make_post(db, admin, title="Sekret", slug="sekret", status=Post.STATUS_DRAFT)
        response = client.get("/feed.xml")
        assert b"Sekret" not in response.data

    def test_draft_hidden_from_tag_view(self, client, db, admin):
        from app.models import Tag

        tag = Tag(name="flask", slug="flask")
        db.session.add(tag)
        db.session.flush()
        post = _make_post(db, admin, title="Szkic", slug="szkic", status=Post.STATUS_DRAFT)
        post.tags = [tag]
        db.session.commit()

        response = client.get("/tag/flask")
        assert b"Szkic" not in response.data

    def test_published_post_is_visible(self, client, db, admin):
        _make_post(db, admin, title="Jawny", slug="jawny", status=Post.STATUS_PUBLISHED)
        assert client.get("/post/jawny").status_code == 200

    def test_draft_absent_from_prev_next_navigation(self, client, db, admin):
        """Nawigacja między wpisami nie może zdradzić tytułu szkicu.

        Sam tytuł w linku "następny wpis" byłby wyciekiem — czytelnik
        dowiedziałby się o treści, której nie opublikowano.
        """
        _make_post(db, admin, title="Starszy", slug="starszy", status=Post.STATUS_PUBLISHED)
        _make_post(db, admin, title="Tajny szkic", slug="tajny", status=Post.STATUS_DRAFT)
        _make_post(db, admin, title="Nowszy", slug="nowszy", status=Post.STATUS_PUBLISHED)

        response = client.get("/post/starszy")
        assert response.status_code == 200
        assert b"Tajny szkic" not in response.data


class TestCsrf:
    def test_delete_rejected_without_csrf_token(self, app, admin):
        """Usuwanie to akcja destrukcyjna — musi wymagać tokenu CSRF."""
        app.config["WTF_CSRF_ENABLED"] = True
        client = app.test_client()
        client.post(
            "/admin/login",
            data={"username": "admin", "password": "correct-horse-battery-staple"},
        )
        response = client.post("/admin/post/1/delete")
        assert response.status_code in (400, 302)
