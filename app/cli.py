import getpass

import click
from argon2 import PasswordHasher

from app.extensions import db
from app.models import Post, Tag, User
from app.utils.sanitize import SANITIZER_VERSION, sanitize_html
from app.utils.slugify import slugify, unique_slug

_hasher = PasswordHasher()


def register(app):
    app.cli.add_command(create_admin)
    app.cli.add_command(seed)
    app.cli.add_command(resanitize)


@click.command("create-admin")
@click.option("--username", prompt=True)
def create_admin(username):
    """Zakłada jedyne konto administratora. Brak rejestracji publicznej."""
    if User.query.filter_by(username=username).first():
        click.echo(f"Użytkownik '{username}' już istnieje.")
        return

    password = getpass.getpass("Hasło: ")
    confirm = getpass.getpass("Powtórz hasło: ")
    if password != confirm:
        click.echo("Hasła się nie zgadzają.")
        return
    if len(password) < 12:
        click.echo("Hasło musi mieć co najmniej 12 znaków.")
        return

    user = User(username=username, password_hash=_hasher.hash(password))
    db.session.add(user)
    db.session.commit()
    click.echo(f"Utworzono konto administratora '{username}'.")


@click.command("seed")
def seed():
    """Dane przykładowe do developmentu — nieprzeznaczone na produkcję."""
    if Post.query.first():
        click.echo("Baza już zawiera wpisy — pomijam.")
        return

    author = User.query.first()
    if author is None:
        click.echo("Najpierw uruchom `flask create-admin`.")
        return

    tag_names = ["case-study", "poradnik", "flask"]
    tags = {}
    for name in tag_names:
        tag = Tag(name=name, slug=slugify(name))
        db.session.add(tag)
        tags[name] = tag

    sample_posts = [
        ("Czym się zajmuję", ["case-study"]),
        ("5 kroków do dobrej strony", ["poradnik"]),
    ]
    for title, tag_keys in sample_posts:
        base_slug = slugify(title)
        slug = unique_slug(
            base_slug,
            lambda s: Post.query.filter_by(slug=s).first() is not None,
        )
        post = Post(
            title=title,
            slug=slug,
            body_source="<p>Treść przykładowa.</p>",
            body_html="<p>Treść przykładowa.</p>",
            excerpt="Wpis przykładowy wygenerowany przez flask seed.",
            tags=[tags[k] for k in tag_keys],
        )
        post.publish()
        db.session.add(post)

    db.session.commit()
    click.echo(f"Dodano {len(sample_posts)} wpisów przykładowych.")


@click.command("resanitize")
@click.option("--force", is_flag=True, help="Przelicz też wpisy z aktualną wersją.")
def resanitize(force):
    """Przelicza body_html z body_source po zmianie reguł sanitizera.

    OBOWIĄZKOWE po każdej zmianie whitelisty w app/utils/sanitize.py —
    zapisany body_html zamraża reguły z momentu zapisu, więc bez tego
    załatana dziura zostaje w starych wpisach (plan, sekcja 7).
    """
    query = Post.query
    if not force:
        query = query.filter(Post.sanitizer_version != SANITIZER_VERSION)

    posts = query.all()
    if not posts:
        click.echo("Wszystkie wpisy są aktualne.")
        return

    changed = 0
    for post in posts:
        new_html = sanitize_html(post.body_source)
        if new_html != post.body_html:
            post.body_html = new_html
            changed += 1
        post.sanitizer_version = SANITIZER_VERSION

    db.session.commit()
    click.echo(
        f"Przetworzono {len(posts)} wpisów (wersja -> {SANITIZER_VERSION}), "
        f"treść zmieniona w {changed}."
    )
