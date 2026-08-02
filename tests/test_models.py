import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Image, Post, Tag


def test_post_publish_sets_published_at_once(db, admin):
    post = Post(
        title="X", slug="x", body_source="<p>x</p>", body_html="<p>x</p>",
        author_id=admin.id,
    )
    assert post.published_at is None
    assert not post.is_published

    post.publish()
    first_published_at = post.published_at
    assert post.is_published
    assert first_published_at is not None

    # Republikacja nie powinna przesuwać daty pierwszej publikacji.
    post.publish()
    assert post.published_at == first_published_at


def test_post_tags_many_to_many(db, admin):
    tag_a = Tag(name="flask", slug="flask")
    tag_b = Tag(name="case-study", slug="case-study")
    db.session.add_all([tag_a, tag_b])
    db.session.flush()

    post = Post(
        title="X", slug="x", body_source="<p>x</p>", body_html="<p>x</p>",
        author_id=admin.id, tags=[tag_a, tag_b],
    )
    db.session.add(post)
    db.session.commit()

    assert set(t.name for t in post.tags) == {"flask", "case-study"}
    assert post in tag_a.posts
    assert post in tag_b.posts


def test_post_slug_must_be_unique(db, admin):
    db.session.add(Post(
        title="X", slug="dup", body_source="", body_html="", author_id=admin.id,
    ))
    db.session.commit()

    db.session.add(Post(
        title="Y", slug="dup", body_source="", body_html="", author_id=admin.id,
    ))
    with pytest.raises(IntegrityError):
        db.session.commit()


def test_deleting_post_cascades_to_images(db, admin):
    post = Post(
        title="X", slug="x", body_source="", body_html="", author_id=admin.id,
    )
    db.session.add(post)
    db.session.flush()
    db.session.add(Image(cloudinary_public_id="p1", url="https://x/y.jpg", post_id=post.id))
    db.session.commit()

    assert Image.query.count() == 1
    db.session.delete(post)
    db.session.commit()
    assert Image.query.count() == 0
