"""Licznik wyświetleń wpisu: deduplikacja przez cookie sesyjne, filtr botów
po User-Agent (patrz record_view() w app/public/queries.py).
"""
from app.models import Post
from app.public.queries import VIEWED_POSTS_COOKIE, record_view
from app.utils.content import is_bot_user_agent


def _publish(db, admin, title="Wpis", slug="wpis"):
    post = Post(
        title=title, slug=slug,
        body_source="<p>tresc</p>", body_html="<p>tresc</p>", author_id=admin.id,
    )
    post.publish()
    db.session.add(post)
    db.session.commit()
    return post


class TestIsBotUserAgent:
    def test_known_bot_detected(self):
        assert is_bot_user_agent("Mozilla/5.0 (compatible; Googlebot/2.1)")
        assert is_bot_user_agent("curl/8.0.1")
        assert is_bot_user_agent("facebookexternalhit/1.1")

    def test_empty_user_agent_is_bot(self):
        assert is_bot_user_agent("") is True
        assert is_bot_user_agent(None) is True

    def test_normal_browser_is_not_bot(self):
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        assert is_bot_user_agent(ua) is False


class TestViewCounterOnPage:
    def test_first_visit_increments_counter(self, client, db, admin):
        post = _publish(db, admin)
        client.get(f"/post/{post.slug}")
        db.session.refresh(post)
        assert post.views_count == 1

    def test_second_visit_same_session_does_not_double_count(self, client, db, admin):
        post = _publish(db, admin)
        client.get(f"/post/{post.slug}")
        client.get(f"/post/{post.slug}")
        db.session.refresh(post)
        assert post.views_count == 1

    def test_sets_viewed_cookie(self, client, db, admin):
        post = _publish(db, admin)
        response = client.get(f"/post/{post.slug}")
        assert VIEWED_POSTS_COOKIE in response.headers.get("Set-Cookie", "")

    def test_bot_user_agent_not_counted(self, client, db, admin):
        post = _publish(db, admin)
        client.get(f"/post/{post.slug}", headers={"User-Agent": "curl/8.0.1"})
        db.session.refresh(post)
        assert post.views_count == 0

    def test_two_different_posts_both_counted_in_same_session(self, client, db, admin):
        first = _publish(db, admin, "Pierwszy", "pierwszy")
        second = _publish(db, admin, "Drugi", "drugi")
        client.get(f"/post/{first.slug}")
        client.get(f"/post/{second.slug}")
        db.session.refresh(first)
        db.session.refresh(second)
        assert first.views_count == 1
        assert second.views_count == 1


_BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


class TestRecordViewFunction:
    def test_returns_none_for_bot(self, app, db, admin):
        post = _publish(db, admin)
        with app.test_request_context(headers={"User-Agent": "Googlebot"}):
            assert record_view(post) is None

    def test_returns_none_when_already_viewed(self, app, db, admin):
        post = _publish(db, admin)
        headers = {"User-Agent": _BROWSER_UA, "Cookie": f"{VIEWED_POSTS_COOKIE}={post.slug}"}
        with app.test_request_context(headers=headers):
            assert record_view(post) is None

    def test_returns_updated_slug_list(self, app, db, admin):
        post = _publish(db, admin)
        headers = {"User-Agent": _BROWSER_UA, "Cookie": f"{VIEWED_POSTS_COOKIE}=inny-slug"}
        with app.test_request_context(headers=headers):
            result = record_view(post)
            assert result == ["inny-slug", post.slug]
