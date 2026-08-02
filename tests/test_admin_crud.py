from datetime import timedelta

from app.models import Post, utcnow


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


class TestTagAutocomplete:
    def test_new_post_form_lists_existing_tag_names(self, auth_client, db):
        from app.models import Tag

        db.session.add(Tag(name="flask", slug="flask"))
        db.session.commit()

        response = auth_client.get("/admin/post/new")
        assert response.status_code == 200
        assert b'<option value="flask">' in response.data

    def test_edit_form_also_lists_existing_tag_names(self, auth_client, db, admin):
        from app.models import Tag

        db.session.add(Tag(name="django", slug="django"))
        post = Post(title="Wpis", slug="wpis", body_source="", body_html="",
                    author_id=admin.id)
        db.session.add(post)
        db.session.commit()

        response = auth_client.get(f"/admin/post/{post.id}/edit")
        assert response.status_code == 200
        assert b'<option value="django">' in response.data


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

    def test_delete_soft_deletes_post_instead_of_removing_it(self, auth_client, db):
        auth_client.post(
            "/admin/post/new",
            data={
                "title": "Do usuniecia", "excerpt": "e", "tags": "",
                "status": "draft", "body_source": "<p>x</p>",
            },
        )
        post = Post.query.filter_by(title="Do usuniecia").first()
        auth_client.post(f"/admin/post/{post.id}/delete")
        db.session.refresh(post)
        assert post.deleted_at is not None
        assert db.session.get(Post, post.id) is not None

    def test_deleted_post_disappears_from_dashboard(self, auth_client, db):
        auth_client.post(
            "/admin/post/new",
            data={
                "title": "Znika z listy", "excerpt": "e", "tags": "",
                "status": "draft", "body_source": "<p>x</p>",
            },
        )
        post = Post.query.filter_by(title="Znika z listy").first()
        auth_client.post(f"/admin/post/{post.id}/delete")

        response = auth_client.get("/admin/")
        assert b"Znika z listy" not in response.data

    def test_deleted_post_edit_returns_404(self, auth_client, db):
        auth_client.post(
            "/admin/post/new",
            data={
                "title": "Bez edycji", "excerpt": "e", "tags": "",
                "status": "draft", "body_source": "<p>x</p>",
            },
        )
        post = Post.query.filter_by(title="Bez edycji").first()
        auth_client.post(f"/admin/post/{post.id}/delete")

        response = auth_client.get(f"/admin/post/{post.id}/edit")
        assert response.status_code == 404

    def test_duplicate_creates_draft_copy_with_new_slug(self, auth_client, db, admin):
        from app.models import Label, Tag

        tag = Tag(name="flask", slug="flask")
        label = Label(name="Eksperyment", slug="eksperyment", color="purple")
        db.session.add_all([tag, label])
        db.session.flush()

        original = Post(
            title="Oryginal", slug="oryginal", excerpt="opis", body_source="<p>x</p>",
            body_html="<p>x</p>", author_id=admin.id, branch="gastronomia",
            is_concept=True, tags=[tag], labels=[label],
        )
        original.publish()
        db.session.add(original)
        db.session.commit()

        response = auth_client.post(
            f"/admin/post/{original.id}/duplicate", follow_redirects=True
        )
        assert response.status_code == 200

        copy = Post.query.filter_by(title="Oryginal (kopia)").first()
        assert copy is not None
        assert copy.id != original.id
        assert copy.slug != original.slug
        assert copy.status == Post.STATUS_DRAFT
        assert copy.published_at is None
        assert copy.excerpt == "opis"
        assert copy.branch == "gastronomia"
        assert copy.is_concept is True
        assert copy.body_html == "<p>x</p>"
        assert {t.name for t in copy.tags} == {"flask"}
        assert {label.name for label in copy.labels} == {"Eksperyment"}

        # oryginał zostaje nietknięty
        db.session.refresh(original)
        assert original.status == Post.STATUS_PUBLISHED

    def test_duplicate_twice_gets_distinct_slugs(self, auth_client, db, admin):
        original = Post(
            title="Powtarzalny", slug="powtarzalny", body_source="", body_html="",
            author_id=admin.id,
        )
        db.session.add(original)
        db.session.commit()

        auth_client.post(f"/admin/post/{original.id}/duplicate")
        auth_client.post(f"/admin/post/{original.id}/duplicate")

        copies = Post.query.filter_by(title="Powtarzalny (kopia)").all()
        assert len(copies) == 2
        assert copies[0].slug != copies[1].slug

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

    def test_search_matches_title(self, auth_client, db, admin):
        db.session.add_all([
            Post(title="Flask od zera", slug="flask-od-zera", body_source="",
                 body_html="", author_id=admin.id),
            Post(title="Zupelnie co innego", slug="co-innego", body_source="",
                 body_html="", author_id=admin.id),
        ])
        db.session.commit()

        response = auth_client.get("/admin/?q=flask")
        assert b"Flask od zera" in response.data
        assert b"Zupelnie co innego" not in response.data

    def test_search_includes_drafts(self, auth_client, db, admin):
        db.session.add(Post(
            title="Szkic o flasku", slug="szkic-o-flasku", body_source="",
            body_html="", author_id=admin.id, status=Post.STATUS_DRAFT,
        ))
        db.session.commit()

        response = auth_client.get("/admin/?q=flasku")
        assert b"Szkic o flasku" in response.data

    def test_kind_filter_narrows_list(self, auth_client, db, admin):
        db.session.add_all([
            Post(title="Notatka", slug="notatka", body_source="", body_html="",
                 author_id=admin.id, kind=Post.KIND_NOTE),
            Post(title="Realizacja", slug="realizacja", body_source="", body_html="",
                 author_id=admin.id, kind=Post.KIND_CASE_STUDY),
        ])
        db.session.commit()

        response = auth_client.get(f"/admin/?kind={Post.KIND_NOTE}")
        assert b"Notatka" in response.data
        assert b"Realizacja" not in response.data

    def test_branch_filter_narrows_list(self, auth_client, db, admin):
        db.session.add_all([
            Post(title="Gastronomia post", slug="gastro", body_source="",
                 body_html="", author_id=admin.id, branch="gastronomia"),
            Post(title="Edukacja post", slug="edu", body_source="",
                 body_html="", author_id=admin.id, branch="edukacja"),
        ])
        db.session.commit()

        response = auth_client.get("/admin/?branch=gastronomia")
        assert b"Gastronomia post" in response.data
        assert b"Edukacja post" not in response.data

    def test_invalid_kind_value_is_ignored(self, auth_client, db, admin):
        db.session.add(Post(
            title="Normalny wpis", slug="normalny", body_source="", body_html="",
            author_id=admin.id,
        ))
        db.session.commit()

        response = auth_client.get("/admin/?kind=../../etc")
        assert response.status_code == 200
        assert b"Normalny wpis" in response.data


class TestDashboardDateColumn:
    def test_shows_updated_at_date(self, auth_client, db, admin):
        post = Post(
            title="Z data", slug="z-data", body_source="", body_html="",
            author_id=admin.id,
        )
        db.session.add(post)
        db.session.commit()

        response = auth_client.get("/admin/")
        assert response.status_code == 200
        expected_date = post.updated_at.strftime("%d.%m.%Y").encode()
        assert expected_date in response.data


class TestDashboardStats:
    def test_counts_drafts_and_published(self, auth_client, db, admin):
        db.session.add_all([
            Post(title="Szkic 1", slug="szkic-1", body_source="", body_html="",
                 author_id=admin.id, status=Post.STATUS_DRAFT),
            Post(title="Szkic 2", slug="szkic-2", body_source="", body_html="",
                 author_id=admin.id, status=Post.STATUS_DRAFT),
        ])
        published = Post(title="Publiczny", slug="publiczny", body_source="",
                          body_html="", author_id=admin.id)
        published.publish()
        db.session.add(published)
        db.session.commit()

        response = auth_client.get("/admin/")
        assert response.status_code == 200
        assert b"<b>2</b> szkice" in response.data
        assert b"<b>1</b> opublikowany" in response.data

    def test_stats_unaffected_by_active_filter(self, auth_client, db, admin):
        published = Post(title="Opublikowany A", slug="opub-a", body_source="",
                          body_html="", author_id=admin.id)
        published.publish()
        db.session.add_all([
            Post(title="Szkic A", slug="szkic-a", body_source="", body_html="",
                 author_id=admin.id, status=Post.STATUS_DRAFT),
            published,
        ])
        db.session.commit()

        response = auth_client.get("/admin/?status=draft")
        assert response.status_code == 200
        # licznik opublikowanych (1) musi być widoczny mimo filtra na szkice
        assert b"<b>1</b> opublikowany" in response.data

    def test_oldest_draft_shown_with_naive_sqlite_datetime(self, auth_client, db, admin):
        """Regresja: SQLite nie zachowuje tzinfo mimo DateTime(timezone=True),
        więc utcnow() - updated_at rzucał TypeError zanim to obsłużono."""
        old_draft = Post(
            title="Stary szkic", slug="stary-szkic", body_source="", body_html="",
            author_id=admin.id, status=Post.STATUS_DRAFT,
        )
        old_draft.updated_at = utcnow().replace(tzinfo=None) - timedelta(days=5)
        db.session.add(old_draft)
        db.session.commit()

        response = auth_client.get("/admin/")
        assert response.status_code == 200
        assert b"Stary szkic" in response.data
        assert b"5 dni temu" in response.data


class TestPostStatusToggle:
    def test_toggle_publishes_draft(self, auth_client, client, db, admin):
        post = Post(
            title="Do publikacji", slug="do-publikacji", body_source="", body_html="",
            author_id=admin.id, status=Post.STATUS_DRAFT,
        )
        db.session.add(post)
        db.session.commit()

        auth_client.post(f"/admin/post/{post.id}/toggle-status")
        db.session.refresh(post)
        assert post.status == Post.STATUS_PUBLISHED
        assert post.published_at is not None
        assert client.get(f"/post/{post.slug}").status_code == 200

    def test_toggle_unpublishes_and_keeps_published_at(self, auth_client, client, db, admin):
        post = Post(
            title="Do cofniecia", slug="do-cofniecia", body_source="", body_html="",
            author_id=admin.id,
        )
        post.publish()
        db.session.add(post)
        db.session.commit()
        first_published_at = post.published_at

        auth_client.post(f"/admin/post/{post.id}/toggle-status")
        db.session.refresh(post)
        assert post.status == Post.STATUS_DRAFT
        assert post.published_at == first_published_at
        assert client.get(f"/post/{post.slug}").status_code == 404

    def test_toggle_redirects_to_filtered_dashboard_via_referrer(self, auth_client, db, admin):
        post = Post(
            title="Filtrowany", slug="filtrowany", body_source="", body_html="",
            author_id=admin.id, status=Post.STATUS_DRAFT,
        )
        db.session.add(post)
        db.session.commit()

        response = auth_client.post(
            f"/admin/post/{post.id}/toggle-status",
            headers={"Referer": "http://localhost/admin/?status=draft"},
        )
        assert response.status_code == 302
        assert response.location == "/admin/?status=draft"

    def test_toggle_ignores_external_referrer(self, auth_client, db, admin):
        post = Post(
            title="Zewnetrzny referrer", slug="zewnetrzny-referrer", body_source="",
            body_html="", author_id=admin.id, status=Post.STATUS_DRAFT,
        )
        db.session.add(post)
        db.session.commit()

        response = auth_client.post(
            f"/admin/post/{post.id}/toggle-status",
            headers={"Referer": "http://evil.example/steal"},
        )
        assert response.status_code == 302
        assert response.location == "/admin/"


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

    def test_essay_kind_is_accepted(self, auth_client, db):
        # Trzeci kind (obok realizacja/notatka) — wpisy niezwiązane z ofertą
        # web-dev, mają pokazać, że silnik obsługuje też długie, swobodne
        # teksty, nie tylko krótkie case studies.
        auth_client.post(
            "/admin/post/new",
            data={
                "title": "Felieton", "excerpt": "e", "tags": "",
                "kind": Post.KIND_ESSAY, "status": "draft",
                "body_source": "<p>x</p>",
            },
        )
        post = Post.query.filter_by(title="Felieton").first()
        assert post.kind == Post.KIND_ESSAY

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


class TestTrash:
    def test_trash_lists_only_deleted_posts(self, auth_client, db, admin):
        kept = Post(
            title="Zyje", slug="zyje", body_source="", body_html="", author_id=admin.id
        )
        deleted = Post(
            title="Usuniety", slug="usuniety", body_source="", body_html="",
            author_id=admin.id,
        )
        deleted.soft_delete()
        db.session.add_all([kept, deleted])
        db.session.commit()

        response = auth_client.get("/admin/kosz")
        assert b"Usuniety" in response.data
        assert b"Zyje" not in response.data

    def test_restore_moves_post_back_to_dashboard_as_draft(self, auth_client, db, admin):
        post = Post(
            title="Do przywrocenia", slug="do-przywrocenia", body_source="",
            body_html="", author_id=admin.id,
        )
        post.publish()
        post.soft_delete()
        db.session.add(post)
        db.session.commit()

        response = auth_client.post(
            f"/admin/post/{post.id}/restore", follow_redirects=True
        )
        assert response.status_code == 200

        db.session.refresh(post)
        assert post.deleted_at is None
        assert post.status == Post.STATUS_DRAFT

        dashboard = auth_client.get("/admin/")
        assert b"Do przywrocenia" in dashboard.data

    def test_restore_on_non_deleted_post_returns_404(self, auth_client, db, admin):
        post = Post(
            title="Nieusuniety", slug="nieusuniety", body_source="", body_html="",
            author_id=admin.id,
        )
        db.session.add(post)
        db.session.commit()

        response = auth_client.post(f"/admin/post/{post.id}/restore")
        assert response.status_code == 404

    def test_purge_permanently_removes_post(self, auth_client, db, admin):
        post = Post(
            title="Do zagłady", slug="do-zaglady", body_source="", body_html="",
            author_id=admin.id,
        )
        post.soft_delete()
        db.session.add(post)
        db.session.commit()
        post_id = post.id

        response = auth_client.post(
            f"/admin/post/{post_id}/purge", follow_redirects=True
        )
        assert response.status_code == 200
        assert db.session.get(Post, post_id) is None

    def test_purge_on_non_deleted_post_returns_404(self, auth_client, db, admin):
        post = Post(
            title="Zywy jeszcze", slug="zywy-jeszcze", body_source="", body_html="",
            author_id=admin.id,
        )
        db.session.add(post)
        db.session.commit()

        response = auth_client.post(f"/admin/post/{post.id}/purge")
        assert response.status_code == 404
        assert db.session.get(Post, post.id) is not None

    def test_dashboard_shows_trash_count(self, auth_client, db, admin):
        post = Post(
            title="W koszu", slug="w-koszu", body_source="", body_html="",
            author_id=admin.id,
        )
        post.soft_delete()
        db.session.add(post)
        db.session.commit()

        response = auth_client.get("/admin/")
        assert b"Kosz (1)" in response.data

    def test_toggle_status_on_deleted_post_returns_404(self, auth_client, db, admin):
        post = Post(
            title="Nie da sie przelaczyc", slug="nie-da-sie-przelaczyc",
            body_source="", body_html="", author_id=admin.id,
        )
        post.soft_delete()
        db.session.add(post)
        db.session.commit()

        response = auth_client.post(f"/admin/post/{post.id}/toggle-status")
        assert response.status_code == 404

    def test_duplicate_of_deleted_post_returns_404(self, auth_client, db, admin):
        post = Post(
            title="Nie do duplikacji", slug="nie-do-duplikacji",
            body_source="", body_html="", author_id=admin.id,
        )
        post.soft_delete()
        db.session.add(post)
        db.session.commit()

        response = auth_client.post(f"/admin/post/{post.id}/duplicate")
        assert response.status_code == 404

    def test_preview_of_deleted_post_returns_404(self, auth_client, db, admin):
        post = Post(
            title="Bez podgladu", slug="bez-podgladu",
            body_source="", body_html="", author_id=admin.id,
        )
        post.soft_delete()
        db.session.add(post)
        db.session.commit()

        response = auth_client.get(f"/admin/post/{post.id}/preview")
        assert response.status_code == 404

    def test_deleted_published_post_disappears_from_public_site(
        self, auth_client, client, db, admin
    ):
        post = Post(
            title="Publiczny znika", slug="publiczny-znika",
            body_source="<p>x</p>", body_html="<p>x</p>", author_id=admin.id,
        )
        post.publish()
        db.session.add(post)
        db.session.commit()

        detail_url = f"/post/{post.slug}"
        assert client.get(detail_url).status_code == 200

        auth_client.post(f"/admin/post/{post.id}/delete")
        assert client.get(detail_url).status_code == 404

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


class TestScheduledPublishing:
    def _datetime_local(self, dt):
        return dt.strftime("%Y-%m-%dT%H:%M")

    def test_create_scheduled_post_via_form(self, auth_client, db):
        future = utcnow() + timedelta(days=1)
        response = auth_client.post(
            "/admin/post/new",
            data={
                "title": "Zaplanowany", "excerpt": "e", "tags": "",
                "status": "scheduled", "scheduled_for": self._datetime_local(future),
                "body_source": "<p>x</p>",
            },
        )
        assert response.status_code == 302
        post = Post.query.filter_by(title="Zaplanowany").first()
        assert post.status == Post.STATUS_SCHEDULED
        assert post.scheduled_for is not None
        assert post.published_at is None

    def test_scheduled_status_with_malformed_date_is_rejected(self, auth_client, db):
        response = auth_client.post(
            "/admin/post/new",
            data={
                "title": "Zla data", "excerpt": "e", "tags": "",
                "status": "scheduled", "scheduled_for": "nie-data",
                "body_source": "<p>x</p>",
            },
        )
        assert response.status_code == 200
        assert Post.query.filter_by(title="Zla data").first() is None

    def test_scheduled_status_without_date_is_rejected(self, auth_client, db):
        auth_client.post(
            "/admin/post/new",
            data={
                "title": "Bez daty", "excerpt": "e", "tags": "",
                "status": "scheduled", "body_source": "<p>x</p>",
            },
        )
        assert Post.query.filter_by(title="Bez daty").first() is None

    def test_scheduled_date_in_the_past_is_rejected(self, auth_client, db):
        past = utcnow() - timedelta(days=1)
        auth_client.post(
            "/admin/post/new",
            data={
                "title": "Data z przeszlosci", "excerpt": "e", "tags": "",
                "status": "scheduled", "scheduled_for": self._datetime_local(past),
                "body_source": "<p>x</p>",
            },
        )
        assert Post.query.filter_by(title="Data z przeszlosci").first() is None

    def test_due_scheduled_post_is_not_public_before_being_read(self, client, db, admin):
        past = utcnow() - timedelta(minutes=5)
        post = Post(
            title="Dojrzaly", slug="dojrzaly", body_source="<p>x</p>",
            body_html="<p>x</p>", author_id=admin.id,
        )
        post.schedule(past)
        db.session.add(post)
        db.session.commit()

        # Zanim ktokolwiek odwiedzi publiczną stronę, status w bazie
        # wciąż jest "scheduled" — promocja jest leniwa, nie ma crona.
        assert db.session.get(Post, post.id).status == Post.STATUS_SCHEDULED

    def test_due_scheduled_post_becomes_visible_after_index_visit(self, client, db, admin):
        past = utcnow() - timedelta(minutes=5)
        post = Post(
            title="Dojrzewa na indeksie", slug="dojrzewa-na-indeksie",
            body_source="<p>x</p>", body_html="<p>x</p>", author_id=admin.id,
        )
        post.schedule(past)
        db.session.add(post)
        db.session.commit()

        response = client.get("/")
        assert b"Dojrzewa na indeksie" in response.data

        db.session.refresh(post)
        assert post.status == Post.STATUS_PUBLISHED
        assert post.scheduled_for is None
        assert post.published_at is not None

    def test_not_yet_due_scheduled_post_stays_hidden(self, client, db, admin):
        future = utcnow() + timedelta(days=1)
        post = Post(
            title="Jeszcze nie", slug="jeszcze-nie",
            body_source="<p>x</p>", body_html="<p>x</p>", author_id=admin.id,
        )
        post.schedule(future)
        db.session.add(post)
        db.session.commit()

        response = client.get("/")
        assert b"Jeszcze nie" not in response.data
        assert client.get("/post/jeszcze-nie").status_code == 404

    def test_toggle_status_on_scheduled_post_publishes_immediately(
        self, auth_client, db, admin
    ):
        future = utcnow() + timedelta(days=1)
        post = Post(
            title="Anuluj harmonogram", slug="anuluj-harmonogram",
            body_source="<p>x</p>", body_html="<p>x</p>", author_id=admin.id,
        )
        post.schedule(future)
        db.session.add(post)
        db.session.commit()

        auth_client.post(f"/admin/post/{post.id}/toggle-status")
        db.session.refresh(post)
        assert post.status == Post.STATUS_PUBLISHED
        assert post.scheduled_for is None

    def test_deleting_scheduled_post_clears_schedule(self, auth_client, db, admin):
        future = utcnow() + timedelta(days=1)
        post = Post(
            title="Do kosza z terminem", slug="do-kosza-z-terminem",
            body_source="<p>x</p>", body_html="<p>x</p>", author_id=admin.id,
        )
        post.schedule(future)
        db.session.add(post)
        db.session.commit()

        auth_client.post(f"/admin/post/{post.id}/delete")
        db.session.refresh(post)
        assert post.status == Post.STATUS_DRAFT
        assert post.scheduled_for is None

    def test_editing_scheduled_post_to_draft_clears_schedule(self, auth_client, db, admin):
        future = utcnow() + timedelta(days=1)
        post = Post(
            title="Wracam do szkicu", slug="wracam-do-szkicu",
            body_source="<p>x</p>", body_html="<p>x</p>", author_id=admin.id,
        )
        post.schedule(future)
        db.session.add(post)
        db.session.commit()

        auth_client.post(
            f"/admin/post/{post.id}/edit",
            data={
                "title": "Wracam do szkicu", "excerpt": "e", "tags": "",
                "status": "draft", "body_source": "<p>x</p>",
            },
        )
        db.session.refresh(post)
        assert post.status == Post.STATUS_DRAFT
        assert post.scheduled_for is None

    def test_dashboard_shows_scheduled_count_and_filter(self, auth_client, db, admin):
        future = utcnow() + timedelta(days=1)
        post = Post(
            title="Widoczny w filtrze", slug="widoczny-w-filtrze",
            body_source="<p>x</p>", body_html="<p>x</p>", author_id=admin.id,
        )
        post.schedule(future)
        db.session.add(post)
        db.session.commit()

        response = auth_client.get("/admin/")
        assert b"1</b> zaplanowany" in response.data or b">1<" in response.data

        filtered = auth_client.get("/admin/?status=scheduled")
        assert b"Widoczny w filtrze" in filtered.data
