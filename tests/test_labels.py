from app.models import Label, Post


def _make_label(db, name="Eksperyment", color="purple"):
    from app.utils.slugify import slugify

    label = Label(name=name, slug=slugify(name), color=color)
    db.session.add(label)
    db.session.commit()
    return label


class TestLabelCrud:
    def test_create_label_via_form(self, auth_client, db):
        auth_client.post(
            "/admin/labels", data={"name": "Eksperyment", "color": "purple"}
        )
        label = Label.query.filter_by(name="Eksperyment").first()
        assert label is not None
        assert label.color == "purple"
        assert label.slug == "eksperyment"

    def test_duplicate_name_is_rejected(self, auth_client, db):
        _make_label(db, name="Eksperyment")
        auth_client.post(
            "/admin/labels", data={"name": "Eksperyment", "color": "green"}
        )
        assert Label.query.filter_by(name="Eksperyment").count() == 1

    def test_edit_updates_name_and_color(self, auth_client, db):
        label = _make_label(db, name="Stary", color="blue")
        auth_client.post(
            f"/admin/labels/{label.id}/edit",
            data={"name": "Nowy", "color": "green"},
        )
        db.session.refresh(label)
        assert label.name == "Nowy"
        assert label.color == "green"
        assert label.slug == "nowy"

    def test_edit_rejects_rename_to_existing_name(self, auth_client, db):
        _make_label(db, name="Zajete", color="blue")
        other = _make_label(db, name="Wolne", color="green")
        auth_client.post(
            f"/admin/labels/{other.id}/edit",
            data={"name": "Zajete", "color": "red"},
        )
        db.session.refresh(other)
        assert other.name == "Wolne"

    def test_delete_removes_label(self, auth_client, db):
        label = _make_label(db)
        auth_client.post(f"/admin/labels/{label.id}/delete")
        assert db.session.get(Label, label.id) is None

    def test_deleting_label_does_not_delete_post(self, auth_client, db, admin):
        label = _make_label(db)
        post = Post(
            title="Ma znaczek", slug="ma-znaczek", body_source="", body_html="",
            author_id=admin.id,
        )
        post.labels = [label]
        db.session.add(post)
        db.session.commit()

        auth_client.post(f"/admin/labels/{label.id}/delete")
        db.session.refresh(post)
        assert db.session.get(Post, post.id) is not None
        assert post.labels == []


class TestLabelMerge:
    def test_merge_moves_posts_and_deletes_source(self, auth_client, db, admin):
        source = _make_label(db, name="Eksperyment")
        target = _make_label(db, name="Do aktualizacji")
        post = Post(
            title="Wpis", slug="wpis", body_source="", body_html="",
            author_id=admin.id, labels=[source],
        )
        db.session.add(post)
        db.session.commit()

        auth_client.post(
            "/admin/labels/merge",
            data={"source_id": source.id, "target_id": target.id},
        )
        db.session.refresh(post)
        assert db.session.get(Label, source.id) is None
        assert {label.name for label in post.labels} == {"Do aktualizacji"}

    def test_merge_does_not_duplicate_when_post_has_both_labels(self, auth_client, db, admin):
        source = _make_label(db, name="Eksperyment")
        target = _make_label(db, name="Do aktualizacji")
        post = Post(
            title="Wpis", slug="wpis", body_source="", body_html="",
            author_id=admin.id, labels=[source, target],
        )
        db.session.add(post)
        db.session.commit()

        auth_client.post(
            "/admin/labels/merge",
            data={"source_id": source.id, "target_id": target.id},
        )
        db.session.refresh(post)
        assert [label.name for label in post.labels] == ["Do aktualizacji"]

    def test_merge_same_label_is_rejected(self, auth_client, db):
        label = _make_label(db, name="Eksperyment")
        response = auth_client.post(
            "/admin/labels/merge",
            data={"source_id": label.id, "target_id": label.id},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert db.session.get(Label, label.id) is not None


class TestPostLabelAssignment:
    def test_assigning_labels_via_post_form(self, auth_client, db):
        label = _make_label(db, name="Eksperyment")
        auth_client.post(
            "/admin/post/new",
            data={
                "title": "Z etykieta", "excerpt": "e", "tags": "",
                "status": "draft", "body_source": "<p>x</p>",
                "labels": [str(label.id)],
            },
        )
        post = Post.query.filter_by(title="Z etykieta").first()
        assert [label.name for label in post.labels] == ["Eksperyment"]

    def test_removing_all_labels_on_edit(self, auth_client, db):
        label = _make_label(db, name="Eksperyment")
        auth_client.post(
            "/admin/post/new",
            data={
                "title": "Odznaczana", "excerpt": "e", "tags": "",
                "status": "draft", "body_source": "<p>x</p>",
                "labels": [str(label.id)],
            },
        )
        post = Post.query.filter_by(title="Odznaczana").first()
        assert post.labels != []

        auth_client.post(
            f"/admin/post/{post.id}/edit",
            data={
                "title": "Odznaczana", "excerpt": "e", "tags": "",
                "status": "draft", "body_source": "<p>x</p>",
            },
        )
        db.session.refresh(post)
        assert post.labels == []

    def test_label_visible_on_published_post_page(self, client, auth_client, db):
        label = _make_label(db, name="Eksperyment", color="amber")
        auth_client.post(
            "/admin/post/new",
            data={
                "title": "Publiczny z etykieta", "excerpt": "e", "tags": "",
                "status": "published", "body_source": "<p>x</p>",
                "labels": [str(label.id)],
            },
        )
        post = Post.query.filter_by(title="Publiczny z etykieta").first()
        response = client.get(f"/post/{post.slug}")
        assert b"Eksperyment" in response.data
        assert b"flag--amber" in response.data
