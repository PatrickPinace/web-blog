from xml.sax.saxutils import escape

from flask import Response, current_app, url_for

from app.models import Tag
from app.public.queries import published_posts_query


def build_sitemap():
    base_url = current_app.config["BLOG_BASE_URL"].rstrip("/")
    posts = published_posts_query().all()
    tags = Tag.query.order_by(Tag.slug).all()

    urls = [
        _url(base_url, url_for("public.index")),
        _url(base_url, url_for("public.about")),
        _url(base_url, url_for("public.tags")),
        _url(base_url, url_for("public.search")),
    ]
    urls += [
        _url(base_url, url_for("public.post_detail", slug=post.slug), post.updated_at)
        for post in posts
    ]
    urls += [
        _url(base_url, url_for("public.tag_detail", slug=tag.slug))
        for tag in tags
    ]

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls)
        + "\n</urlset>\n"
    )
    return Response(xml, mimetype="application/xml")


def _url(base_url, path, lastmod=None):
    loc = f"{base_url}{path}"
    lastmod_tag = f"\n    <lastmod>{lastmod.date().isoformat()}</lastmod>" if lastmod else ""
    return f"  <url>\n    <loc>{escape(loc)}</loc>{lastmod_tag}\n  </url>"
