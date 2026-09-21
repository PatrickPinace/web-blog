"""/realizacje: dedykowany indeks case studies, pogrupowany po branży."""
from app.models import Post
from app.public.queries import UNBRANCHED_LABEL, get_case_studies_by_branch


def _publish(db, admin, title, slug, kind=Post.KIND_CASE_STUDY, branch=None, status=Post.STATUS_PUBLISHED):
    post = Post(
        title=title, slug=slug, kind=kind, branch=branch,
        body_source="<p>tresc</p>", body_html="<p>tresc</p>", author_id=admin.id,
    )
    if status == Post.STATUS_PUBLISHED:
        post.publish()
    else:
        post.status = status
    db.session.add(post)
    db.session.commit()
    return post


class TestGetCaseStudiesByBranch:
    def test_groups_by_branch(self, db, admin):
        _publish(db, admin, "A", "a", branch="sport")
        _publish(db, admin, "B", "b", branch="edukacja")

        groups = dict(get_case_studies_by_branch())
        assert [p.title for p in groups["sport"]] == ["A"]
        assert [p.title for p in groups["edukacja"]] == ["B"]

    def test_branches_ordered_alphabetically(self, db, admin):
        _publish(db, admin, "A", "a", branch="zoo")
        _publish(db, admin, "B", "b", branch="apteka")

        branches = [b for b, _ in get_case_studies_by_branch()]
        assert branches == ["apteka", "zoo"]

    def test_unbranched_case_study_falls_into_catchall_group(self, db, admin):
        _publish(db, admin, "Bez branży", "bez-branzy", branch=None)
        groups = dict(get_case_studies_by_branch())
        assert [p.title for p in groups[UNBRANCHED_LABEL]] == ["Bez branży"]

    def test_unbranched_group_is_last(self, db, admin):
        _publish(db, admin, "A", "a", branch=None)
        _publish(db, admin, "B", "b", branch="apteka")
        branches = [b for b, _ in get_case_studies_by_branch()]
        assert branches[-1] == UNBRANCHED_LABEL

    def test_excludes_non_case_study_kinds(self, db, admin):
        _publish(db, admin, "Notatka", "notatka", kind=Post.KIND_NOTE, branch="sport")
        groups = dict(get_case_studies_by_branch())
        assert "sport" not in groups

    def test_excludes_drafts(self, db, admin):
        _publish(db, admin, "Szkic", "szkic", branch="sport", status=Post.STATUS_DRAFT)
        groups = dict(get_case_studies_by_branch())
        assert "sport" not in groups

    def test_newest_first_within_group(self, db, admin):
        first = _publish(db, admin, "Starszy", "starszy", branch="sport")
        second = _publish(db, admin, "Nowszy", "nowszy", branch="sport")
        groups = dict(get_case_studies_by_branch())
        assert [p.id for p in groups["sport"]] == [second.id, first.id]


class TestCaseStudiesPage:
    def test_returns_200(self, client):
        assert client.get("/realizacje").status_code == 200

    def test_shows_case_study_grouped_under_branch_heading(self, client, db, admin):
        _publish(db, admin, "Kwiaciarnia", "kwiaciarnia", branch="kwiaciarnia")
        body = client.get("/realizacje").get_data(as_text=True)
        assert "kwiaciarnia" in body
        assert "Kwiaciarnia" in body

    def test_notes_and_essays_never_appear(self, client, db, admin):
        _publish(db, admin, "Notatka", "notatka", kind=Post.KIND_NOTE, branch="sport")
        body = client.get("/realizacje").get_data(as_text=True)
        assert "Notatka" not in body

    def test_empty_state_when_no_case_studies(self, client):
        body = client.get("/realizacje").get_data(as_text=True)
        assert "Nie ma jeszcze opublikowanych realizacji" in body

    def test_linked_from_main_navigation(self, client):
        body = client.get("/").get_data(as_text=True)
        assert 'href="/realizacje"' in body
