from app.models import Post

POSTS_PER_PAGE = 10


def published_posts_query():
    """Bazowe zapytanie o wpisy widoczne publicznie.

    Cały ruch publiczny MUSI przechodzić przez tę funkcję — draft nie może
    wyciec przez żadną publiczną ścieżkę, nawet po zgadnięciu sluga.
    """
    return Post.query.filter_by(status=Post.STATUS_PUBLISHED).order_by(
        Post.published_at.desc()
    )


def get_published_post_or_404(slug):
    return published_posts_query().filter_by(slug=slug).first_or_404()
