import getpass

import click
from argon2 import PasswordHasher

from app.extensions import db
from app.models import Post, Tag, User
from app.utils.slugify import slugify, unique_slug

_hasher = PasswordHasher()


def register(app):
    app.cli.add_command(create_admin)
    app.cli.add_command(seed)


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
