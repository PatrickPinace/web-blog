"""Znaczek "Zaktualizowano X temu" — tylko na notatkach technicznych,
tylko gdy wpis realnie był edytowany po publikacji.
"""
from datetime import timedelta

from app.models import Post, utcnow


def _publish(db, admin, title, slug, kind=Post.KIND_NOTE):
    post = Post(
        title=title, slug=slug, kind=kind,
        body_source="<p>tresc</p>", body_html="<p>tresc</p>", author_id=admin.id,
    )
    post.publish()
    db.session.add(post)
    db.session.commit()
    return post


class TestUpdatedNotice:
    def test_shown_on_note_updated_after_publish(self, client, db, admin):
        post = _publish(db, admin, "Notatka", "notatka")
        post.updated_at = utcnow() + timedelta(days=1)
        db.session.commit()

        body = client.get(f"/post/{post.slug}").get_data(as_text=True)
        assert "Zaktualizowano" in body

    def test_hidden_when_never_updated_after_publish(self, client, db, admin):
        post = _publish(db, admin, "Notatka", "notatka")
        body = client.get(f"/post/{post.slug}").get_data(as_text=True)
        assert "Zaktualizowano" not in body

    def test_hidden_on_case_study_even_if_updated(self, client, db, admin):
        post = _publish(db, admin, "Realizacja", "realizacja", kind=Post.KIND_CASE_STUDY)
        post.updated_at = utcnow() + timedelta(days=1)
        db.session.commit()

        body = client.get(f"/post/{post.slug}").get_data(as_text=True)
        assert "Zaktualizowano" not in body

    def test_hidden_on_essay_even_if_updated(self, client, db, admin):
        post = _publish(db, admin, "Felieton", "felieton", kind=Post.KIND_ESSAY)
        post.updated_at = utcnow() + timedelta(days=1)
        db.session.commit()

        body = client.get(f"/post/{post.slug}").get_data(as_text=True)
        assert "Zaktualizowano" not in body
