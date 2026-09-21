"""Filtrowanie strony głównej po branży, i skrócony pasek najpopularniejszych
tagów — reguły dodane, żeby indeks realizacji nie rozjeżdżał się przy dużej
liczbie wpisów (patrz app/public/queries.py: TOP_TAGS_LIMIT).
"""
from app.models import Post, Tag
from app.public.queries import get_top_tags
from app.utils.slugify import slugify


def _publish(db, admin, title, branch=None, tags=None, status=Post.STATUS_PUBLISHED):
    post = Post(
        title=title, slug=slugify(title), branch=branch,
        body_source="", body_html="", author_id=admin.id,
    )
    if status == Post.STATUS_PUBLISHED:
        post.publish()
    else:
        post.status = status
    if tags:
        post.tags = [
            Tag.query.filter_by(name=t).first() or Tag(name=t, slug=slugify(t))
            for t in tags
        ]
    db.session.add(post)
    db.session.commit()
    return post


class TestGetTopTags:
    def test_orders_by_post_count_descending(self, db, admin):
        _publish(db, admin, "A", tags=["popularny", "rzadki"])
        _publish(db, admin, "B", tags=["popularny"])

        names = [t.name for t in get_top_tags()]
        assert names[0] == "popularny"
        assert "rzadki" in names

    def test_respects_limit(self, db, admin):
        for i in range(5):
            _publish(db, admin, f"Wpis {i}", tags=[f"tag{i}"])
        assert len(get_top_tags(limit=3)) == 3

    def test_tags_only_on_drafts_are_excluded(self, db, admin):
        draft = Post(
            title="Szkic", slug="szkic", body_source="", body_html="",
            author_id=admin.id,
        )
        draft.tags = [Tag(name="tylko-szkic", slug="tylko-szkic")]
        db.session.add(draft)
        db.session.commit()
        assert get_top_tags() == []


class TestIndexBranchFilter:
    def test_filters_posts_by_branch(self, client, db, admin):
        _publish(db, admin, "Kwiaciarnia", branch="kwiaciarstwo")
        _publish(db, admin, "Szkoła", branch="edukacja")

        response = client.get("/?branza=edukacja")
        body = response.get_data(as_text=True)
        assert "Szkoła" in body
        assert "Kwiaciarnia" not in body

    def test_unknown_branch_returns_empty_list_not_error(self, client, db, admin):
        _publish(db, admin, "Coś", branch="gastronomia")
        response = client.get("/?branza=nieistniejaca")
        assert response.status_code == 200
        assert "Coś" not in response.get_data(as_text=True)

    def test_branch_filter_survives_pagination_link(self, client, db, admin):
        for i in range(12):
            _publish(db, admin, f"Wpis edukacyjny {i}", branch="edukacja")
        for i in range(3):
            _publish(db, admin, f"Wpis gastro {i}", branch="gastronomia")

        response = client.get("/?branza=edukacja")
        body = response.get_data(as_text=True)
        assert "branza=edukacja" in body
        assert "page=2" in body

    def test_no_branch_filter_shows_everything(self, client, db, admin):
        _publish(db, admin, "A", branch="gastronomia")
        _publish(db, admin, "B", branch="edukacja")
        response = client.get("/")
        body = response.get_data(as_text=True)
        assert "A" in body and "B" in body

    def test_branch_switcher_lists_only_branches_with_published_posts(self, client, db, admin):
        _publish(db, admin, "A", branch="gastronomia")
        _publish(db, admin, "B", branch="edukacja")
        draft = _publish(db, admin, "Szkic", branch="tylko-szkic", status=Post.STATUS_DRAFT)
        response = client.get("/")
        body = response.get_data(as_text=True)
        assert "gastronomia" in body
        assert "edukacja" in body
        assert "tylko-szkic" not in body

    def test_branch_filter_shows_notice_and_return_link(self, client, db, admin):
        _publish(db, admin, "A", branch="gastronomia")
        body = client.get("/?branza=gastronomia").get_data(as_text=True)
        assert "Wpisy dla branży: gastronomia" in body
        assert "Pokaż wszystkie wpisy" in body


def _publish_kind(db, admin, title, kind, status=Post.STATUS_PUBLISHED):
    post = Post(
        title=title, slug=slugify(title), kind=kind,
        body_source="", body_html="", author_id=admin.id,
    )
    if status == Post.STATUS_PUBLISHED:
        post.publish()
    else:
        post.status = status
    db.session.add(post)
    db.session.commit()
    return post


class TestIndexKindFilter:
    def test_filters_posts_by_kind(self, client, db, admin):
        _publish_kind(db, admin, "Felieton", Post.KIND_ESSAY)
        _publish_kind(db, admin, "Notatka", Post.KIND_NOTE)

        response = client.get("/?typ=felieton")
        body = response.get_data(as_text=True)
        assert "Felieton" in body
        assert "Notatka" not in body

    def test_unknown_kind_is_ignored_not_error(self, client, db, admin):
        _publish_kind(db, admin, "Coś", Post.KIND_NOTE)
        response = client.get("/?typ=nieistniejacy")
        assert response.status_code == 200
        assert "Coś" in response.get_data(as_text=True)

    def test_kind_and_branch_filters_combine(self, client, db, admin):
        post = Post(
            title="Realizacja sportowa", slug="realizacja-sportowa",
            kind=Post.KIND_CASE_STUDY, branch="sport",
            body_source="", body_html="", author_id=admin.id,
        )
        post.publish()
        db.session.add(post)
        other = Post(
            title="Notatka sportowa", slug="notatka-sportowa",
            kind=Post.KIND_NOTE, branch="sport",
            body_source="", body_html="", author_id=admin.id,
        )
        other.publish()
        db.session.add(other)
        db.session.commit()

        body = client.get("/?typ=realizacja&branza=sport").get_data(as_text=True)
        assert "Realizacja sportowa" in body
        assert "Notatka sportowa" not in body

    def test_kind_switcher_lists_counts_and_excludes_drafts(self, client, db, admin):
        _publish_kind(db, admin, "F1", Post.KIND_ESSAY)
        _publish_kind(db, admin, "F2", Post.KIND_ESSAY)
        _publish_kind(db, admin, "Szkic", Post.KIND_ESSAY, status=Post.STATUS_DRAFT)
        body = client.get("/").get_data(as_text=True)
        assert "felieton (2)" in body

    def test_kind_filter_shows_notice_and_return_link(self, client, db, admin):
        _publish_kind(db, admin, "Coś", Post.KIND_NOTE)
        body = client.get("/?typ=notatka").get_data(as_text=True)
        assert "Wpisy: notatka" in body
        assert "Pokaż wszystkie wpisy" in body


class TestTagDetailKeepsSelectedTagVisible:
    def test_tag_outside_top_n_still_marked_active_on_its_own_page(self, client, db, admin):
        # 9 różnych tagów na 9 różnych wpisach - jeden na pewno wypadnie
        # z domyślnego TOP_TAGS_LIMIT (8), ale musi zostać widoczny (i
        # aktywny) na WŁASNEJ stronie tagu, inaczej pasek filtrów "gubi"
        # aktualnie przeglądany tag.
        posts = [_publish(db, admin, f"Wpis {i}", tags=[f"tag{i}"]) for i in range(9)]
        rare_tag = posts[-1].tags[0]

        response = client.get(f"/tag/{rare_tag.slug}")
        assert response.status_code == 200
        body = response.get_data(as_text=True)
        assert rare_tag.name in body
        # Tag musi wystąpić jako link w pasku filtrów, nie tylko gdzieś
        # w treści strony (np. przypadkiem w tytule wpisu).
        assert f'href="/tag/{rare_tag.slug}"' in body
