"""Tryb demo (User.is_demo) — konto pokazowe dla odwiedzających: prawdziwa
edycja treści, ale bez uploadu obrazków, bez niszczenia struktury tagów/
etykiet, i z filtrem wulgaryzmów przy zapisie. Patrz app/demo.py.
"""
import io

from app.demo import contains_profanity, reset_demo_content
from app.models import Label, Post, Tag


def _create(client, title="Wpis demo", body="<p>tresc</p>", excerpt="e"):
    client.post(
        "/admin/post/new",
        data={
            "title": title, "excerpt": excerpt, "tags": "",
            "status": "draft", "body_source": body,
        },
    )
    return Post.query.filter_by(title=title).first()


class TestDemoCanEdit:
    """Rdzeń doświadczenia demo musi działać — inaczej to nie jest demo."""

    def test_demo_can_create_post(self, demo_client, db):
        post = _create(demo_client, title="Nowy wpis demo")
        assert post is not None
        assert post.body_source == "<p>tresc</p>"

    def test_demo_can_edit_post(self, demo_client, db, demo_user):
        post = _create(demo_client)
        response = demo_client.post(
            f"/admin/post/{post.id}/edit",
            data={
                "title": post.title, "excerpt": "nowy opis", "tags": "",
                "status": "draft", "body_source": post.body_source,
            },
        )
        db.session.refresh(post)
        assert response.status_code == 302
        assert post.excerpt == "nowy opis"

    def test_demo_can_toggle_status(self, demo_client, db):
        post = _create(demo_client)
        response = demo_client.post(f"/admin/post/{post.id}/toggle-status")
        db.session.refresh(post)
        assert response.status_code == 302
        assert post.status == Post.STATUS_PUBLISHED

    def test_demo_can_soft_delete(self, demo_client, db):
        """Kosz jest odwracalny i reset i tak sprząta bazę co godzinę —
        w przeciwieństwie do purge, to nie wymaga blokady."""
        post = _create(demo_client)
        response = demo_client.post(f"/admin/post/{post.id}/delete")
        db.session.refresh(post)
        assert response.status_code == 302
        assert post.deleted_at is not None


class TestDemoForbidden:
    """Akcje, których skutek reset bazy NIE cofa (Cloudinary) albo które
    psują demo dla następnego odwiedzającego przed najbliższym resetem."""

    def test_demo_cannot_upload_image(self, demo_client, db):
        response = demo_client.post(
            "/admin/upload-image",
            data={"file": (io.BytesIO(b"fake"), "test.png")},
            content_type="multipart/form-data",
        )
        assert response.status_code == 403

    def test_demo_cannot_embed_youtube(self, demo_client, db):
        response = demo_client.post(
            "/admin/embed-youtube",
            data={"url": "https://youtube.com/watch?v=abc"},
        )
        assert response.status_code == 403

    def test_demo_cannot_purge_post(self, demo_client, db):
        post = _create(demo_client)
        demo_client.post(f"/admin/post/{post.id}/delete")
        response = demo_client.post(f"/admin/post/{post.id}/purge")
        assert response.status_code == 403
        assert Post.query.filter_by(id=post.id).first() is not None

    def test_demo_cannot_add_label(self, demo_client, db):
        response = demo_client.post(
            "/admin/labels", data={"name": "nowy", "color": "#000000"}
        )
        assert response.status_code == 403
        assert Label.query.filter_by(name="nowy").first() is None

    def test_demo_can_still_view_labels_list(self, demo_client, db):
        """@demo_forbidden blokuje tylko POST — GET musi zostać przeglądalny."""
        response = demo_client.get("/admin/labels")
        assert response.status_code == 200

    def test_demo_cannot_delete_label(self, demo_client, db):
        label = Label(name="test", slug="test", color="#000000")
        db.session.add(label)
        db.session.commit()
        response = demo_client.post(f"/admin/labels/{label.id}/delete")
        assert response.status_code == 403
        assert Label.query.filter_by(id=label.id).first() is not None

    def test_demo_cannot_delete_tag(self, demo_client, db):
        tag = Tag(name="test", slug="test")
        db.session.add(tag)
        db.session.commit()
        response = demo_client.post(f"/admin/tags/{tag.id}/delete")
        assert response.status_code == 403
        assert Tag.query.filter_by(id=tag.id).first() is not None

    def test_demo_cannot_merge_tags(self, demo_client, db):
        source = Tag(name="a", slug="a")
        target = Tag(name="b", slug="b")
        db.session.add_all([source, target])
        db.session.commit()
        response = demo_client.post(
            "/admin/tags/merge",
            data={"source_id": source.id, "target_id": target.id},
        )
        assert response.status_code == 403
        assert Tag.query.filter_by(id=source.id).first() is not None


class TestAdminUnaffected:
    """Prawdziwy admin nie jest tknięty żadną z tych blokad."""

    def test_admin_can_upload_related_route_not_blocked(self, auth_client, db):
        # Bez realnego pliku/Cloudinary — sprawdzamy tylko, że request NIE
        # dostaje 403 z demo_forbidden (upload_image sam zwróci 400 na braku
        # pliku, co jest oczekiwane i niezwiązane z trybem demo).
        response = auth_client.post("/admin/upload-image", data={})
        assert response.status_code != 403

    def test_admin_can_delete_label(self, auth_client, db):
        label = Label(name="test", slug="test", color="#000000")
        db.session.add(label)
        db.session.commit()
        response = auth_client.post(f"/admin/labels/{label.id}/delete")
        assert response.status_code == 302
        assert Label.query.filter_by(id=label.id).first() is None


class TestProfanityFilter:
    def test_contains_profanity_detects_blocked_word(self):
        assert contains_profanity("to jest kurwa test") is True

    def test_contains_profanity_case_insensitive(self):
        assert contains_profanity("KURWA") is True

    def test_contains_profanity_clean_text(self):
        assert contains_profanity("to jest czysty tekst o Flasku") is False

    def test_contains_profanity_does_not_match_substring_of_innocent_word(self):
        # "chuj" nie powinno łapać się w słowach niezwiązanych, ale samo
        # słowo z dowolnym sufiksem (\w*) powinno się złapać.
        assert contains_profanity("chujowy dzień") is True
        assert contains_profanity("nic złego tutaj") is False

    def test_demo_cannot_save_profanity_in_body(self, demo_client, db):
        response = demo_client.post(
            "/admin/post/new",
            data={
                "title": "Test", "excerpt": "e", "tags": "",
                "status": "draft", "body_source": "<p>to jest kurwa złe</p>",
            },
        )
        assert response.status_code == 200  # walidacja nie przechodzi, re-render formularza
        assert Post.query.filter_by(title="Test").first() is None

    def test_demo_cannot_save_profanity_in_title(self, demo_client, db):
        response = demo_client.post(
            "/admin/post/new",
            data={
                "title": "Chujowy wpis", "excerpt": "e", "tags": "",
                "status": "draft", "body_source": "<p>tresc</p>",
            },
        )
        assert response.status_code == 200
        assert Post.query.filter_by(title="Chujowy wpis").first() is None

    def test_admin_can_save_text_that_would_be_blocked_for_demo(self, auth_client, db):
        """Filtr jest specyficzny dla demo — prawdziwy admin nie jest nim
        ograniczony (to nie jest ogólna moderacja treści bloga)."""
        post = _create(auth_client, title="Wpis admina", body="<p>kurwa</p>")
        assert post is not None
        assert "kurwa" in post.body_source


class TestResetDemoContent:
    """Regresja: Query.delete() (bulk) omija ORM cascade na tabelach
    asocjacyjnych post_tags/post_labels — bez jawnego czyszczenia tych
    tabel drugi reset z rzędu wywalał się na UNIQUE constraint, bo SQLite
    bez AUTOINCREMENT oddaje te same id po DELETE."""

    def test_reset_restores_seed_posts(self, admin, db):
        reset_demo_content()
        posts = Post.query.all()
        assert len(posts) == 11
        assert {p.title for p in posts} == {
            "Czym się zajmuję",
            "5 pytań, zanim wycenisz nową stronę",
            "Kwiaciarnia: strona, która ma pokazać towar",
            "Szkoła językowa: trzy warianty, jeden wybór",
            "Klub sportowy: pokazać system, nie opisać go",
            "BDO bez BDO: rejestrowanie odbioru odpadów bez zgadywania statusu",
            "Jak zbudowany jest ten serwis",
            "Superpozycja: czym jest i skąd się wzięła",
            "Co potrafi ten blog: przewodnik po funkcjach i o tym, co jest "
            "zablokowane w demo",
            "Portal tenisowy: rezerwacje i ranking Elo zamiast arkusza i telefonu",
            "SubForge: napisy dopasowane po hashu pliku, nie po zgadywaniu tytułu",
        }

    def test_reset_twice_in_a_row_does_not_crash(self, admin, db):
        """To dokładnie ten scenariusz, który złapał bug z post_tags —
        drugi reset musi przejść tak samo czysto jak pierwszy."""
        reset_demo_content()
        reset_demo_content()
        assert Post.query.count() == 11

    def test_reset_clears_content_added_via_demo(self, demo_client, db, admin):
        _create(demo_client, title="Wpis od odwiedzającego")
        assert Post.query.filter_by(title="Wpis od odwiedzającego").first() is not None

        reset_demo_content()

        assert Post.query.filter_by(title="Wpis od odwiedzającego").first() is None
        assert Post.query.count() == 11

    def test_reset_preserves_user_accounts(self, admin, demo_user, db):
        from app.models import User

        reset_demo_content()
        assert User.query.filter_by(username=admin.username).first() is not None
        assert User.query.filter_by(username=demo_user.username).first() is not None


class TestLoginHint:
    """Podpowiedź danych demo na /admin/login — widoczna tylko gdy
    DEMO_MODE aktywne, żeby ktoś testujący link nie musiał pytać o dostęp."""

    def test_hint_hidden_by_default(self, client, app):
        assert app.config["DEMO_MODE"] is False
        response = client.get("/admin/login")
        assert b"To wersja demo" not in response.data

    def test_hint_shown_when_demo_mode_enabled(self, client, app):
        app.config["DEMO_MODE"] = True
        app.config["DEMO_USERNAME"] = "demo"
        app.config["DEMO_PASSWORD_HINT"] = "haslo123"
        response = client.get("/admin/login")
        assert b"To wersja demo" in response.data
        assert b"demo" in response.data
        assert b"haslo123" in response.data
