from app.models import Post, Tag


def _make_tag(db, name="flask"):
    from app.utils.slugify import slugify

    tag = Tag(name=name, slug=slugify(name))
    db.session.add(tag)
    db.session.commit()
    return tag


class TestTagsList:
    def test_shows_post_count_per_tag(self, auth_client, db, admin):
        tag = _make_tag(db, "flask")
        post = Post(
            title="Wpis", slug="wpis", body_source="", body_html="",
            author_id=admin.id, tags=[tag],
        )
        db.session.add(post)
        db.session.commit()

        response = auth_client.get("/admin/tags")
        assert response.status_code == 200
        assert b"flask" in response.data

    def test_unused_tag_shows_zero_count(self, auth_client, db):
        _make_tag(db, "nieuzywany")
        response = auth_client.get("/admin/tags")
        assert response.status_code == 200
        assert b"nieuzywany" in response.data


class TestTagRename:
    def test_rename_updates_name_and_slug(self, auth_client, db):
        tag = _make_tag(db, "stary")
        auth_client.post(f"/admin/tags/{tag.id}/rename", data={"name": "nowy"})
        db.session.refresh(tag)
        assert tag.name == "nowy"
        assert tag.slug == "nowy"

    def test_rename_to_existing_name_is_rejected(self, auth_client, db):
        _make_tag(db, "zajety")
        other = _make_tag(db, "wolny")
        auth_client.post(f"/admin/tags/{other.id}/rename", data={"name": "zajety"})
        db.session.refresh(other)
        assert other.name == "wolny"

    def test_rename_preserves_post_associations(self, auth_client, db, admin):
        tag = _make_tag(db, "stary")
        post = Post(
            title="Wpis", slug="wpis", body_source="", body_html="",
            author_id=admin.id, tags=[tag],
        )
        db.session.add(post)
        db.session.commit()

        auth_client.post(f"/admin/tags/{tag.id}/rename", data={"name": "nowy"})
        db.session.refresh(post)
        assert {t.name for t in post.tags} == {"nowy"}


class TestTagMerge:
    def test_merge_moves_posts_and_deletes_source(self, auth_client, db, admin):
        source = _make_tag(db, "flask-blog")
        target = _make_tag(db, "flask")
        post = Post(
            title="Wpis", slug="wpis", body_source="", body_html="",
            author_id=admin.id, tags=[source],
        )
        db.session.add(post)
        db.session.commit()

        auth_client.post(
            "/admin/tags/merge",
            data={"source_id": source.id, "target_id": target.id},
        )
        db.session.refresh(post)
        assert db.session.get(Tag, source.id) is None
        assert {t.name for t in post.tags} == {"flask"}

    def test_merge_does_not_duplicate_when_post_has_both_tags(self, auth_client, db, admin):
        source = _make_tag(db, "flask-blog")
        target = _make_tag(db, "flask")
        post = Post(
            title="Wpis", slug="wpis", body_source="", body_html="",
            author_id=admin.id, tags=[source, target],
        )
        db.session.add(post)
        db.session.commit()

        auth_client.post(
            "/admin/tags/merge",
            data={"source_id": source.id, "target_id": target.id},
        )
        db.session.refresh(post)
        assert [t.name for t in post.tags] == ["flask"]

    def test_merge_same_tag_is_rejected(self, auth_client, db):
        tag = _make_tag(db, "flask")
        response = auth_client.post(
            "/admin/tags/merge",
            data={"source_id": tag.id, "target_id": tag.id},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert db.session.get(Tag, tag.id) is not None


class TestTagDelete:
    def test_delete_removes_tag(self, auth_client, db):
        tag = _make_tag(db, "usuwany")
        auth_client.post(f"/admin/tags/{tag.id}/delete")
        assert db.session.get(Tag, tag.id) is None

    def test_delete_tag_does_not_delete_post(self, auth_client, db, admin):
        tag = _make_tag(db, "flask")
        post = Post(
            title="Wpis", slug="wpis", body_source="", body_html="",
            author_id=admin.id, tags=[tag],
        )
        db.session.add(post)
        db.session.commit()

        auth_client.post(f"/admin/tags/{tag.id}/delete")
        db.session.refresh(post)
        assert db.session.get(Post, post.id) is not None
        assert post.tags == []
