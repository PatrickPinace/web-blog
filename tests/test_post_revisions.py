"""Wersjonowanie treści (PostRevision) — snapshot przed każdą zmianą treści,
przywracanie, ochrona przed niesanitowanym HTML w podglądzie.
"""
from app.models import Post, PostRevision


def _create(auth_client, title="Wpis", body="<p>tresc v1</p>", excerpt="e"):
    auth_client.post(
        "/admin/post/new",
        data={
            "title": title, "excerpt": excerpt, "tags": "",
            "status": "draft", "body_source": body,
        },
    )
    return Post.query.filter_by(title=title).first()


def _edit(auth_client, post, **overrides):
    data = {
        "title": post.title, "excerpt": post.excerpt or "", "tags": "",
        "status": post.status, "body_source": post.body_source,
    }
    data.update(overrides)
    return auth_client.post(f"/admin/post/{post.id}/edit", data=data)


class TestRevisionCreatedOnBodyChange:
    def test_no_revision_on_create(self, auth_client, db):
        post = _create(auth_client, title="Nowy wpis")
        assert PostRevision.query.filter_by(post_id=post.id).count() == 0

    def test_revision_created_when_body_changes(self, auth_client, db):
        post = _create(auth_client, title="Wpis A", body="<p>v1</p>")
        _edit(auth_client, post, body_source="<p>v2</p>")
        db.session.refresh(post)

        revisions = PostRevision.query.filter_by(post_id=post.id).all()
        assert len(revisions) == 1
        assert revisions[0].body_source == "<p>v1</p>"
        assert post.body_source == "<p>v2</p>"

    def test_no_revision_when_body_unchanged(self, auth_client, db):
        post = _create(auth_client, title="Wpis B", body="<p>stała treść</p>")
        _edit(auth_client, post, excerpt="inny opis")
        db.session.refresh(post)

        assert PostRevision.query.filter_by(post_id=post.id).count() == 0

    def test_each_body_change_adds_new_revision(self, auth_client, db):
        post = _create(auth_client, title="Wpis C", body="<p>v1</p>")
        _edit(auth_client, post, body_source="<p>v2</p>")
        db.session.refresh(post)
        _edit(auth_client, post, body_source="<p>v3</p>")
        db.session.refresh(post)

        revisions = PostRevision.query.filter_by(post_id=post.id).order_by(
            PostRevision.id
        ).all()
        assert [r.body_source for r in revisions] == ["<p>v1</p>", "<p>v2</p>"]
        assert post.body_source == "<p>v3</p>"

    def test_revision_snapshots_title_and_excerpt_too(self, auth_client, db):
        post = _create(auth_client, title="Stary tytuł", body="<p>v1</p>", excerpt="stary opis")
        _edit(auth_client, post, title="Stary tytuł", excerpt="nowy opis", body_source="<p>v2</p>")
        db.session.refresh(post)

        revision = PostRevision.query.filter_by(post_id=post.id).first()
        assert revision.title == "Stary tytuł"
        assert revision.excerpt == "stary opis"


class TestRevisionRestore:
    def test_restore_brings_back_old_content(self, auth_client, db):
        post = _create(auth_client, title="Wpis D", body="<p>oryginał</p>")
        _edit(auth_client, post, body_source="<p>zmienione</p>")
        db.session.refresh(post)
        revision = PostRevision.query.filter_by(post_id=post.id).first()

        auth_client.post(f"/admin/post/{post.id}/revision/{revision.id}/restore")
        db.session.refresh(post)

        assert post.body_source == "<p>oryginał</p>"
        assert "<p>oryginał</p>" in post.body_html

    def test_restore_creates_new_revision_of_content_before_restore(self, auth_client, db):
        post = _create(auth_client, title="Wpis E", body="<p>v1</p>")
        _edit(auth_client, post, body_source="<p>v2</p>")
        db.session.refresh(post)
        revision_v1 = PostRevision.query.filter_by(post_id=post.id).first()

        auth_client.post(f"/admin/post/{post.id}/revision/{revision_v1.id}/restore")
        db.session.refresh(post)

        revisions = PostRevision.query.filter_by(post_id=post.id).order_by(
            PostRevision.id
        ).all()
        # v1 (oryginalna) + v2 (zapisana jako snapshot przed przywróceniem)
        assert [r.body_source for r in revisions] == ["<p>v1</p>", "<p>v2</p>"]
        assert post.body_source == "<p>v1</p>"

    def test_restore_does_not_change_slug(self, auth_client, db):
        post = _create(auth_client, title="Tytuł oryginalny", body="<p>v1</p>")
        _edit(auth_client, post, title="Zmieniony tytuł", body_source="<p>v2</p>")
        db.session.refresh(post)
        slug_after_edit = post.slug
        revision = PostRevision.query.filter_by(post_id=post.id).first()

        auth_client.post(f"/admin/post/{post.id}/revision/{revision.id}/restore")
        db.session.refresh(post)

        # Tytuł wraca do "Tytuł oryginalny" (z revision), ale slug NIE jest
        # przeliczany przy przywracaniu — zostaje ten sam, co był tuż przed
        # przywróceniem (ustawiony przy edycji), żeby nie łamać linków.
        assert post.title == "Tytuł oryginalny"
        assert post.slug == slug_after_edit

    def test_restore_does_not_change_status(self, auth_client, db):
        post = _create(auth_client, title="Wpis F", body="<p>v1</p>")
        _edit(auth_client, post, body_source="<p>v2</p>", status="published")
        db.session.refresh(post)
        revision = PostRevision.query.filter_by(post_id=post.id).first()

        auth_client.post(f"/admin/post/{post.id}/revision/{revision.id}/restore")
        db.session.refresh(post)

        assert post.status == Post.STATUS_PUBLISHED

    def test_restore_wrong_post_id_returns_404(self, auth_client, db):
        post_a = _create(auth_client, title="Wpis G", body="<p>v1</p>")
        _edit(auth_client, post_a, body_source="<p>v2</p>")
        db.session.refresh(post_a)
        revision = PostRevision.query.filter_by(post_id=post_a.id).first()

        post_b = _create(auth_client, title="Wpis H", body="<p>inny</p>")

        response = auth_client.post(
            f"/admin/post/{post_b.id}/revision/{revision.id}/restore"
        )
        assert response.status_code == 404

    def test_restore_requires_login(self, client, db, admin):
        post = Post(
            title="Wpis I", slug="wpis-i",
            body_source="<p>x</p>", body_html="<p>x</p>", author_id=admin.id,
        )
        db.session.add(post)
        db.session.commit()

        response = client.post(f"/admin/post/{post.id}/revision/1/restore")
        assert response.status_code in (302, 401)


class TestRevisionPreviewIsSanitized:
    def test_script_tag_stripped_from_history_page(self, auth_client, db):
        post = _create(auth_client, title="Wpis J", body="<p>v1</p>")
        _edit(auth_client, post, body_source='<p>v2</p><script>alert(1)</script>')
        db.session.refresh(post)

        response = auth_client.get(f"/admin/post/{post.id}/historia")
        assert b"<script>alert(1)</script>" not in response.data
