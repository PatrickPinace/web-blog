"""/portfolio.json: realizacje jako ustrukturyzowany JSON."""
from app.models import Post


def _publish(db, admin, title, slug, kind=Post.KIND_CASE_STUDY, branch=None):
    post = Post(
        title=title, slug=slug, kind=kind, branch=branch,
        body_source="<p>tresc</p>", body_html="<p>tresc</p>", author_id=admin.id,
    )
    post.publish()
    db.session.add(post)
    db.session.commit()
    return post


class TestPortfolioJson:
    def test_lists_only_case_studies(self, client, db, admin):
        _publish(db, admin, "Realizacja", "realizacja")
        _publish(db, admin, "Notatka", "notatka", kind=Post.KIND_NOTE)
        _publish(db, admin, "Felieton", "felieton", kind=Post.KIND_ESSAY)

        response = client.get("/portfolio.json")
        data = response.get_json()
        titles = [r["title"] for r in data["realizacje"]]
        assert "Realizacja" in titles
        assert "Notatka" not in titles
        assert "Felieton" not in titles

    def test_excludes_drafts(self, client, db, admin):
        post = Post(
            title="Szkic", slug="szkic",
            body_source="", body_html="", author_id=admin.id,
        )
        db.session.add(post)
        db.session.commit()

        response = client.get("/portfolio.json")
        titles = [r["title"] for r in response.get_json()["realizacje"]]
        assert "Szkic" not in titles

    def test_entry_has_full_url_and_fields(self, client, db, admin):
        _publish(db, admin, "Kwiaciarnia", "kwiaciarnia", branch="kwiaciarnia")
        entry = client.get("/portfolio.json").get_json()["realizacje"][0]
        assert entry["branch"] == "kwiaciarnia"
        assert entry["url"].endswith("/post/kwiaciarnia")
        assert "published_at" in entry
        assert "is_concept" in entry

    def test_empty_when_no_case_studies(self, client, db, admin):
        _publish(db, admin, "Notatka", "notatka", kind=Post.KIND_NOTE)
        response = client.get("/portfolio.json")
        assert response.get_json()["realizacje"] == []
