"""Tryb demo: konto pokazowe dla odwiedzających, bez logowania jako
właściwy admin (patrz User.is_demo w app/models.py).

Trzy warstwy ochrony:
1. @demo_forbidden — blokuje całe akcje (upload, tagi/etykiety, trwałe
   usuwanie) niezależnie od resetu, bo część skutków (Cloudinary) reset
   bazy i tak by nie cofnął.
2. filter_profanity — prosty check listy słów przy zapisie treści, żeby
   skrócić czas ekspozycji niestosownego tekstu z godziny (do resetu)
   do natychmiast.
3. reset_demo_content (wołane przez `flask reset-demo`, patrz app/cli.py)
   — czyści wpisy/tagi/etykiety dodane w trakcie i przywraca seed.
"""
from functools import wraps

from flask import abort
from flask_login import current_user

# Lista celowo krótka i bez wulgaryzmów religijnych/etnicznych osobno —
# to nie ma być filtr treści w ogóle, tylko odsianie oczywistego spamu
# wulgarnego na publicznym demo. Dopasowanie case-insensitive, z granicami
# słów, żeby nie łapać fragmentów niewinnych wyrazów.
_BLOCKED_WORDS = [
    "kurwa", "chuj", "pierdol", "jebac", "jebań", "jebani", "jeban",
    "spierdal", "skurwysyn", "suka", "cipa", "pojeb",
    "fuck", "shit", "asshole", "bitch", "cunt",
]


def contains_profanity(*texts):
    """True, jeśli którykolwiek z tekstów zawiera słowo z listy."""
    import re

    pattern = r"\b(?:" + "|".join(_BLOCKED_WORDS) + r")\w*"
    combined = " ".join(t or "" for t in texts).lower()
    return re.search(pattern, combined) is not None


def demo_forbidden(view):
    """Blokuje akcję dla konta demo (403), niezależnie od reset-u bazy —
    dla akcji, których skutek reset nie cofa (upload na Cloudinary) albo
    które psują demo dla kogoś, kto zajrzy przed najbliższym resetem
    (usunięcie struktury tagów/etykiet).

    Blokuje tylko POST — widoki GET+POST na tym samym endpoincie (np.
    /labels: GET listuje, POST dodaje) muszą zostać przeglądalne dla demo,
    tylko zapis jest zabroniony."""
    from flask import request

    @wraps(view)
    def wrapped(*args, **kwargs):
        if (
            request.method == "POST"
            and current_user.is_authenticated
            and current_user.is_demo
        ):
            abort(403, description="Ta akcja jest wyłączona w trybie demo.")
        return view(*args, **kwargs)

    return wrapped


def reset_demo_content():
    """Przywraca bazę do stanu seed — wołane co godzinę przez `flask
    reset-demo`. Zostawia konta użytkowników (admin + demo) nietknięte,
    czyści tylko treść, którą mógł nabazgrać ktoś w panelu demo.

    Tabele asocjacyjne (post_tags, post_labels) NIE mają ORM cascade na
    bulk delete() — Query.delete() pomija Python-side cascade, więc bez
    jawnego czyszczenia tych tabel osierocone wiersze (post_id, tag_id)
    zderzają się z ID-kami nowo wstawionych wierszy po re-seedzie
    (UNIQUE constraint failed), bo SQLite w tym projekcie nie ma
    AUTOINCREMENT i chętnie odda ten sam id od nowa."""
    from app.extensions import db
    from app.models import (
        Label,
        Post,
        PostActivity,
        PostRevision,
        Tag,
        post_labels,
        post_tags,
    )

    db.session.execute(post_tags.delete())
    db.session.execute(post_labels.delete())
    PostRevision.query.delete()
    PostActivity.query.delete()
    Post.query.delete()
    Tag.query.delete()
    Label.query.delete()
    db.session.commit()

    from app.cli import _seed_posts

    _seed_posts()
