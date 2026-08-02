from app.models import Post


class TestLogin:
    def test_wrong_password_shows_error_without_session(self, client, admin):
        response = client.post(
            "/admin/login", data={"username": "admin", "password": "wrong"}
        )
        assert response.status_code == 200
        assert b"Nieprawid" in response.data

    def test_correct_password_logs_in(self, client, admin):
        response = client.post(
            "/admin/login",
            data={"username": "admin", "password": "correct-horse-battery-staple"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        # dashboard dostępny bez kolejnego redirectu na /admin/login
        assert response.request.path == "/admin/"


class TestPostCrud:
    def test_create_post_generates_slug_and_sanitizes(self, auth_client, db):
        auth_client.post(
            "/admin/post/new",
            data={
                "title": "Mój Pierwszy Wpis",
                "excerpt": "Opis",
                "tags": "flask, test",
                "status": "draft",
                "body_source": "<p>Tresc <script>alert(1)</script></p>",
            },
        )
        post = Post.query.filter_by(title="Mój Pierwszy Wpis").first()
        assert post is not None
        assert post.slug == "moj-pierwszy-wpis"
        assert post.status == Post.STATUS_DRAFT
        assert "<script>" not in post.body_html
        assert "<script>alert(1)</script>" in post.body_source
        assert {t.name for t in post.tags} == {"flask", "test"}

    def test_edit_recalculates_slug_on_title_change(self, auth_client, db):
        auth_client.post(
            "/admin/post/new",
            data={
                "title": "Stary tytul", "excerpt": "e", "tags": "",
                "status": "draft", "body_source": "<p>x</p>",
            },
        )
        post = Post.query.filter_by(title="Stary tytul").first()
        old_slug = post.slug

        auth_client.post(
            f"/admin/post/{post.id}/edit",
            data={
                "title": "Nowy tytul", "excerpt": "e", "tags": "",
                "status": "draft", "body_source": "<p>x</p>",
            },
        )
        db.session.refresh(post)
        assert post.title == "Nowy tytul"
        assert post.slug != old_slug
        assert post.slug == "nowy-tytul"

    def test_edit_without_title_change_keeps_slug(self, auth_client, db):
        auth_client.post(
            "/admin/post/new",
            data={
                "title": "Stabilny tytul", "excerpt": "stary", "tags": "",
                "status": "draft", "body_source": "<p>x</p>",
            },
        )
        post = Post.query.filter_by(title="Stabilny tytul").first()
        original_slug = post.slug

        auth_client.post(
            f"/admin/post/{post.id}/edit",
            data={
                "title": "Stabilny tytul", "excerpt": "nowy opis", "tags": "",
                "status": "draft", "body_source": "<p>x</p>",
            },
        )
        db.session.refresh(post)
        assert post.slug == original_slug
        assert post.excerpt == "nowy opis"

    def test_publish_sets_published_at_and_makes_post_public(self, auth_client, client, db):
        auth_client.post(
            "/admin/post/new",
            data={
                "title": "Do publikacji", "excerpt": "e", "tags": "",
                "status": "draft", "body_source": "<p>x</p>",
            },
        )
        post = Post.query.filter_by(title="Do publikacji").first()
        assert client.get(f"/post/{post.slug}").status_code == 404

        auth_client.post(
            f"/admin/post/{post.id}/edit",
            data={
                "title": "Do publikacji", "excerpt": "e", "tags": "",
                "status": "published", "body_source": "<p>x</p>",
            },
        )
        db.session.refresh(post)
        assert post.published_at is not None
        assert client.get(f"/post/{post.slug}").status_code == 200

    def test_delete_removes_post(self, auth_client, db):
        auth_client.post(
            "/admin/post/new",
            data={
                "title": "Do usuniecia", "excerpt": "e", "tags": "",
                "status": "draft", "body_source": "<p>x</p>",
            },
        )
        post = Post.query.filter_by(title="Do usuniecia").first()
        auth_client.post(f"/admin/post/{post.id}/delete")
        assert db.session.get(Post, post.id) is None

    def test_reusing_tag_name_does_not_duplicate_tag(self, auth_client, db):
        from app.models import Tag

        auth_client.post(
            "/admin/post/new",
            data={
                "title": "Post A", "excerpt": "", "tags": "flask",
                "status": "draft", "body_source": "<p>x</p>",
            },
        )
        auth_client.post(
            "/admin/post/new",
            data={
                "title": "Post B", "excerpt": "", "tags": "flask",
                "status": "draft", "body_source": "<p>x</p>",
            },
        )
        assert Tag.query.filter_by(name="flask").count() == 1


class TestDashboardFilter:
    def test_status_filter_shows_only_matching_posts(self, auth_client, db, admin):
        draft = Post(
            title="Szkic", slug="szkic", body_source="", body_html="",
            author_id=admin.id, status=Post.STATUS_DRAFT,
        )
        published = Post(
            title="Publiczny", slug="publiczny", body_source="", body_html="",
            author_id=admin.id,
        )
        published.publish()
        db.session.add_all([draft, published])
        db.session.commit()

        response = auth_client.get("/admin/?status=draft")
        assert b"Szkic" in response.data
        assert b"Publiczny" not in response.data


class TestPostMetadataFields:
    """kind / branch / is_concept — pola dodane razem z designem (etap 6a)."""

    def test_kind_defaults_when_absent_from_form(self, auth_client, db):
        auth_client.post(
            "/admin/post/new",
            data={
                "title": "Bez kind", "excerpt": "e", "tags": "",
                "status": "draft", "body_source": "<p>x</p>",
            },
        )
        post = Post.query.filter_by(title="Bez kind").first()
        assert post.kind == Post.KIND_CASE_STUDY
        assert post.is_concept is False
        assert post.branch is None

    def test_kind_rejects_value_outside_choices(self, auth_client, db):
        auth_client.post(
            "/admin/post/new",
            data={
                "title": "Zly kind", "excerpt": "e", "tags": "",
                "kind": "../../etc", "status": "draft",
                "body_source": "<p>x</p>",
            },
        )
        assert Post.query.filter_by(title="Zly kind").first() is None

    def test_blank_branch_is_stored_as_null(self, auth_client, db):
        auth_client.post(
            "/admin/post/new",
            data={
                "title": "Pusta branza", "excerpt": "e", "tags": "",
                "branch": "   ", "status": "draft",
                "body_source": "<p>x</p>",
            },
        )
        post = Post.query.filter_by(title="Pusta branza").first()
        assert post.branch is None

    def test_unchecking_is_concept_clears_the_flag(self, auth_client, db):
        auth_client.post(
            "/admin/post/new",
            data={
                "title": "Koncepcyjny", "excerpt": "e", "tags": "",
                "is_concept": "y", "status": "draft",
                "body_source": "<p>x</p>",
            },
        )
        post = Post.query.filter_by(title="Koncepcyjny").first()
        assert post.is_concept is True

        # Odznaczony checkbox nie jest w ogóle wysyłany przez przeglądarkę.
        auth_client.post(
            f"/admin/post/{post.id}/edit",
            data={
                "title": "Koncepcyjny", "excerpt": "e", "tags": "",
                "status": "draft", "body_source": "<p>x</p>",
            },
        )
        db.session.refresh(post)
        assert post.is_concept is False
