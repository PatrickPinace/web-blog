"""Wyszukiwanie: dokładne dopasowanie substring + fuzzy fallback (trigramy).

Reguła testowana explicite: fuzzy fallback uruchamia się TYLKO gdy dopasowanie
dokładne zwróci zero wyników — inaczej literówka w jednym słowie potrafiłaby
podmienić sensowne, precyzyjne wyniki na coś przypadkowo podobnego.
"""
from app.models import Post
from app.utils.search import normalize, search_posts, trigram_similarity


class FakePost:
    """Search operuje na atrybutach Post (title/excerpt/tags/slug), nie na
    ORM-owym query — testujemy więc bez bazy, żeby sprawdzić samą logikę."""

    def __init__(self, title, excerpt="", tags=(), slug=None):
        self.title = title
        self.excerpt = excerpt
        self.tags = [_FakeTag(t) for t in tags]
        self.slug = slug or title


class _FakeTag:
    def __init__(self, name):
        self.name = name


class TestNormalize:
    def test_strips_polish_diacritics(self):
        assert normalize("Wzięła Łódź") == "wziela lodz"

    def test_lowercases(self):
        assert normalize("WYCENISZ") == "wycenisz"


class TestTrigramSimilarity:
    def test_identical_strings_are_one(self):
        assert trigram_similarity("wycenisz", "wycenisz") == 1.0

    def test_unrelated_strings_are_low(self):
        assert trigram_similarity("wycenisz", "kwiaciarnia") < 0.2

    def test_one_letter_typo_stays_similar(self):
        # "wyceniesz" -> "wycenisz" - jedna literówka, powinno zostać wysoko.
        assert trigram_similarity("wyceniesz", "wycenisz") > 0.5


class TestSearchPosts:
    def test_matches_title_case_insensitively(self):
        posts = [FakePost("Superpozycja: czym jest"), FakePost("Kwiaciarnia")]
        assert search_posts(posts, "SUPERPOZYCJA") == [posts[0]]

    def test_matches_excerpt(self):
        posts = [FakePost("Tytuł", excerpt="wspomina o rankingu Elo")]
        assert search_posts(posts, "ranking") == posts

    def test_matches_tag_name(self):
        posts = [FakePost("Tytuł", tags=["case-study"]), FakePost("Inny")]
        assert search_posts(posts, "case-study") == [posts[0]]

    def test_all_tokens_must_match_somewhere(self):
        posts = [FakePost("Szkoła językowa: trzy warianty")]
        assert search_posts(posts, "szkoła warianty") == posts
        assert search_posts(posts, "szkoła kwiaciarnia") == []

    def test_ignores_polish_diacritics_in_query(self):
        posts = [FakePost("Szkoła językowa")]
        assert search_posts(posts, "jezykowa") == posts

    def test_empty_query_returns_nothing(self):
        assert search_posts([FakePost("Coś")], "") == []
        assert search_posts([FakePost("Coś")], "   ") == []

    def test_typo_falls_back_to_fuzzy_match(self):
        posts = [FakePost("5 pytań, zanim wycenisz nową stronę")]
        # "wyceniejsz" nie istnieje dosłownie w tytule - dokładne dopasowanie
        # zwraca zero, fuzzy fallback powinien i tak znaleźć ten wpis.
        assert search_posts(posts, "wyceniejsz") == posts

    def test_exact_match_wins_over_fuzzy_when_both_possible(self):
        # Gdy dopasowanie dokładne istnieje, fuzzy fallback się NIE odpala -
        # więc wpis z samą literówką w innym miejscu nie wpycha się do wyników.
        exact = FakePost("Wycenisz stronę")
        posts = [exact, FakePost("Coś całkiem innego o kotach")]
        assert search_posts(posts, "wycenisz") == [exact]

    def test_completely_unrelated_query_returns_nothing(self):
        posts = [FakePost("Kwiaciarnia: strona, która ma pokazać towar")]
        assert search_posts(posts, "dynozaury") == []

    def test_short_tokens_are_not_used_for_fuzzy_fallback(self):
        # Tokeny < 4 znaków nie wchodzą do fuzzy (za duże ryzyko przypadkowych
        # trafień) - fallback z samym krótkim słowem powinien dać zero, nie
        # losowe dopasowania.
        posts = [FakePost("Zupełnie inny tytuł")]
        assert search_posts(posts, "xyz") == []


class TestSearchRoute:
    def _publish(self, db, admin, title, excerpt="", tags=None):
        post = Post(
            title=title, slug=title.lower().replace(" ", "-"),
            excerpt=excerpt, body_source="", body_html="", author_id=admin.id,
        )
        post.publish()
        if tags:
            from app.models import Tag
            from app.utils.slugify import slugify

            post.tags = [
                Tag.query.filter_by(name=t).first() or Tag(name=t, slug=slugify(t))
                for t in tags
            ]
        db.session.add(post)
        db.session.commit()
        return post

    def test_search_page_without_query_shows_prompt(self, client):
        response = client.get("/szukaj")
        assert response.status_code == 200
        assert "szukan" in response.get_data(as_text=True).lower()

    def test_search_finds_published_post_by_title(self, client, db, admin):
        self._publish(db, admin, "Kwiaciarnia: strona, która ma pokazać towar")
        response = client.get("/szukaj?q=kwiaciarnia")
        assert response.status_code == 200
        assert "Kwiaciarnia" in response.get_data(as_text=True)

    def test_search_does_not_leak_drafts(self, client, db, admin):
        draft = Post(
            title="Szkic o tajnym projekcie", slug="szkic-tajny",
            body_source="", body_html="", author_id=admin.id,
        )
        db.session.add(draft)
        db.session.commit()

        response = client.get("/szukaj?q=tajnym")
        assert response.status_code == 200
        assert "Szkic o tajnym projekcie" not in response.get_data(as_text=True)


class TestTagsRoute:
    def test_lists_only_tags_used_by_published_posts(self, client, db, admin):
        from app.models import Tag
        from app.utils.slugify import slugify

        used_tag = Tag(name="case-study", slug=slugify("case-study"))
        orphan_tag = Tag(name="nieużywany", slug=slugify("nieużywany"))
        db.session.add_all([used_tag, orphan_tag])

        post = Post(
            title="Wpis", slug="wpis", body_source="", body_html="",
            author_id=admin.id,
        )
        post.publish()
        post.tags = [used_tag]
        db.session.add(post)
        db.session.commit()

        response = client.get("/tagi")
        body = response.get_data(as_text=True)
        assert "case-study" in body
        assert "nieużywany" not in body

    def test_renders_filter_input_and_data_attrs_for_js(self, client, db, admin):
        """main.js filtruje tagi po `data-tag-name` w [data-tag-cloud] —
        bez tych atrybutów filtr renderuje się, ale nic nie robi."""
        from app.models import Tag
        from app.utils.slugify import slugify

        tag = Tag(name="flask", slug=slugify("flask"))
        db.session.add(tag)
        post = Post(
            title="Wpis", slug="wpis", body_source="", body_html="",
            author_id=admin.id,
        )
        post.publish()
        post.tags = [tag]
        db.session.add(post)
        db.session.commit()

        body = client.get("/tagi").get_data(as_text=True)
        assert "data-tag-filter" in body
        assert "data-tag-cloud" in body
        assert 'data-tag-name="flask"' in body
