from xml.sax.saxutils import escape

from flask import Response, current_app, url_for

from app.public.queries import published_posts_query

FEED_ITEM_LIMIT = 20


def build_rss_feed():
    posts = published_posts_query().limit(FEED_ITEM_LIMIT).all()
    base_url = current_app.config["BLOG_BASE_URL"].rstrip("/")

    items = "\n".join(_render_item(post, base_url) for post in posts)

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>{escape(current_app.config["BLOG_TITLE"])}</title>
    <link>{escape(base_url)}</link>
    <description>{escape(current_app.config["BLOG_DESCRIPTION"])}</description>
{items}
  </channel>
</rss>
"""
    return Response(xml, mimetype="application/rss+xml")


def _render_item(post, base_url):
    link = f"{base_url}{url_for('public.post_detail', slug=post.slug)}"
    pub_date = post.published_at.strftime("%a, %d %b %Y %H:%M:%S %z")
    description = escape(post.excerpt or "")
    return f"""    <item>
      <title>{escape(post.title)}</title>
      <link>{escape(link)}</link>
      <guid>{escape(link)}</guid>
      <pubDate>{pub_date}</pubDate>
      <description>{description}</description>
    </item>"""
