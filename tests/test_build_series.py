"""Seria o budowie bloga używa dokładnie tych samych zasad publiczności co reszta widoków."""
from datetime import timedelta

from app.models import Post, utcnow
from app.public.queries import get_blog_build_series_posts


def _post(db, admin, title, slug, *, published=True):
    post = Post(
        title=title,
        slug=slug,
        body_source="<h2>Sekcja</h2><p>Treść</p>",
        body_html="<h2>Sekcja</h2><p>Treść</p>",
        author_id=admin.id,
    )
    if published:
        post.publish()
    db.session.add(post)
    db.session.commit()
    return post


def _series_slugs(app, *slugs):
    app.config["BLOG_BUILD_SERIES_SLUGS"] = slugs


class TestBuildSeriesVisibility:
    def test_empty_series_has_no_public_parts_and_home_keeps_about_link(self, app, client):
        _series_slugs(app)

        assert get_blog_build_series_posts() == []
        body = client.get("/").get_data(as_text=True)
        assert 'href="/about">Przejdź do wprowadzenia' in body
        assert "Pierwsze części serii są w przygotowaniu." in client.get("/about").get_data(as_text=True)

    def test_keeps_configuration_order_not_publication_order(self, app, client, db, admin):
        second = _post(db, admin, "Druga część", "druga")
        first = _post(db, admin, "Pierwsza część", "pierwsza")
        _series_slugs(app, first.slug, second.slug)

        assert [post.slug for post in get_blog_build_series_posts()] == ["pierwsza", "druga"]
        body = client.get("/about").get_data(as_text=True)
        assert body.index("Pierwsza część") < body.index("Druga część")
        home = client.get("/").get_data(as_text=True)
        assert 'href="/post/pierwsza">Przejdź do wprowadzenia' in home

    def test_missing_slug_is_silently_skipped(self, app, db, admin):
        post = _post(db, admin, "Dostępna część", "dostepna")
        _series_slugs(app, "nie-ma-takiego-wpisu", post.slug)

        assert get_blog_build_series_posts() == [post]

    def test_draft_and_deleted_posts_never_leak_into_series(self, app, client, db, admin):
        visible = _post(db, admin, "Widoczna część", "widoczna")
        draft = _post(db, admin, "Tajny szkic", "szkic", published=False)
        deleted = _post(db, admin, "Część w koszu", "kosz")
        deleted.soft_delete()
        db.session.commit()
        _series_slugs(app, draft.slug, deleted.slug, visible.slug)

        assert get_blog_build_series_posts() == [visible]
        about = client.get("/about").get_data(as_text=True)
        assert "Widoczna część" in about
        assert "Tajny szkic" not in about
        assert "Część w koszu" not in about

    def test_future_scheduled_post_stays_hidden(self, app, db, admin):
        post = _post(db, admin, "Przyszła część", "przyszla", published=False)
        post.schedule(utcnow() + timedelta(days=1))
        db.session.commit()
        _series_slugs(app, post.slug)

        assert get_blog_build_series_posts() == []

    def test_due_scheduled_post_is_promoted_by_shared_public_query(self, app, db, admin):
        post = _post(db, admin, "Dojrzała część", "dojrzala", published=False)
        post.schedule(utcnow() - timedelta(minutes=1))
        db.session.commit()
        _series_slugs(app, post.slug)

        assert get_blog_build_series_posts() == [post]
        db.session.refresh(post)
        assert post.status == Post.STATUS_PUBLISHED


class TestBuildSeriesNavigation:
    def test_series_navigation_follows_series_order(self, app, client, db, admin):
        first = _post(db, admin, "Pierwsza", "pierwsza")
        second = _post(db, admin, "Druga", "druga")
        _series_slugs(app, second.slug, first.slug)

        body = client.get(f"/post/{second.slug}").get_data(as_text=True)
        assert "Następna część" in body
        assert f'href="/post/{first.slug}"' in body
        assert "Poprzedni" not in body

    def test_non_series_post_keeps_chronological_navigation(self, app, client, db, admin):
        older = _post(db, admin, "Starszy", "starszy")
        outside = _post(db, admin, "Poza serią", "poza-seria")
        _series_slugs(app, older.slug)

        body = client.get(f"/post/{outside.slug}").get_data(as_text=True)
        assert "Poprzedni" in body
        assert "część" not in body
