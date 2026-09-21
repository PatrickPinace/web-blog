"""Powiązane wpisy na stronie artykułu: wspólny tag, bez bieżącego wpisu,
bez szkiców/kosza (patrz app/public/queries.py: get_related_posts).
"""
from app.models import Post, Tag
from app.public.queries import get_related_posts
from app.utils.slugify import slugify


def _make_post(db, admin, title, tags=None, status=Post.STATUS_PUBLISHED):
    post = Post(
        title=title, slug=slugify(title),
        body_source="", body_html="", author_id=admin.id,
    )
    if tags:
        post.tags = [
            Tag.query.filter_by(name=t).first() or Tag(name=t, slug=slugify(t))
            for t in tags
        ]
    db.session.add(post)
    db.session.flush()
    if status == Post.STATUS_PUBLISHED:
        post.publish()
    db.session.commit()
    return post


class TestGetRelatedPosts:
    def test_finds_post_with_shared_tag(self, db, admin):
        post = _make_post(db, admin, "Główny", tags=["flask"])
        other = _make_post(db, admin, "Inny", tags=["flask"])
        assert other in get_related_posts(post)

    def test_excludes_current_post(self, db, admin):
        post = _make_post(db, admin, "Główny", tags=["flask"])
        assert post not in get_related_posts(post)

    def test_no_tags_returns_empty(self, db, admin):
        post = _make_post(db, admin, "Bez tagów")
        _make_post(db, admin, "Inny", tags=["flask"])
        assert get_related_posts(post) == []

    def test_unrelated_tags_not_included(self, db, admin):
        post = _make_post(db, admin, "Główny", tags=["flask"])
        unrelated = _make_post(db, admin, "Niepowiązany", tags=["django"])
        assert unrelated not in get_related_posts(post)

    def test_draft_with_shared_tag_excluded(self, db, admin):
        post = _make_post(db, admin, "Główny", tags=["flask"])
        _make_post(db, admin, "Szkic", tags=["flask"], status=Post.STATUS_DRAFT)
        assert get_related_posts(post) == []

    def test_respects_limit(self, db, admin):
        post = _make_post(db, admin, "Główny", tags=["flask"])
        for i in range(5):
            _make_post(db, admin, f"Inny {i}", tags=["flask"])
        assert len(get_related_posts(post, limit=3)) == 3


class TestRelatedPostsOnPage:
    def test_section_rendered_when_related_exist(self, client, db, admin):
        post = _make_post(db, admin, "Główny", tags=["flask"])
        other = _make_post(db, admin, "Inny wpis", tags=["flask"])
        response = client.get(f"/post/{post.slug}")
        assert b"Zobacz te" in response.data
        assert other.title.encode() in response.data

    def test_section_absent_without_related(self, client, db, admin):
        post = _make_post(db, admin, "Samotny")
        response = client.get(f"/post/{post.slug}")
        assert b"Zobacz te" not in response.data
