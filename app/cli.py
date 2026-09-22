import getpass
import json
from pathlib import Path

import click
from argon2 import PasswordHasher

from app.extensions import db
from app.models import Post, Tag, User
from app.utils.sanitize import SANITIZER_VERSION, sanitize_html
from app.utils.slugify import slugify, unique_slug

_DEMO_POSTS_FIXTURE = Path(__file__).parent / "fixtures" / "demo_posts.json"

_hasher = PasswordHasher()


def register(app):
    app.cli.add_command(create_admin)
    app.cli.add_command(seed)
    app.cli.add_command(resanitize)
    app.cli.add_command(reset_demo)
    app.cli.add_command(create_demo_user)


@click.command("create-demo-user")
@click.option("--username", default="demo")
@click.option("--password", envvar="DEMO_PASSWORD", required=True)
def create_demo_user(username, password):
    """Zakłada konto demo (is_demo=True) — hasło z --password albo env
    DEMO_PASSWORD, nie promptowane: musi dać się wywołać nieinteraktywnie
    przy starcie kontenera produkcyjnego trybu demo."""
    existing = User.query.filter_by(username=username).first()
    if existing is not None:
        if not existing.is_demo:
            click.echo(
                f"Użytkownik '{username}' już istnieje i NIE jest kontem demo "
                "— pomijam, żeby nie nadpisać prawdziwego admina."
            )
            return
        click.echo(f"Konto demo '{username}' już istnieje.")
        return

    user = User(username=username, password_hash=_hasher.hash(password), is_demo=True)
    db.session.add(user)
    db.session.commit()
    click.echo(f"Utworzono konto demo '{username}'.")


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


def _seed_posts():
    """Wgrywa wpisy z app/fixtures/demo_posts.json (prawdziwa treść bloga,
    wyeksportowana z bazy deweloperskiej) — używane zarówno przez `flask
    seed` (development), jak i reset_demo_content() (patrz app/demo.py).
    Zakłada pustą tabelę Post/Tag — nie sprawdza duplikatów.
    """
    author = User.query.first()
    if author is None:
        click.echo("Najpierw uruchom `flask create-admin`.")
        return 0

    posts_data = json.loads(_DEMO_POSTS_FIXTURE.read_text(encoding="utf-8"))
    tags_cache = {}

    for entry in posts_data:
        tag_objs = []
        for name in entry["tags"]:
            if name not in tags_cache:
                tag = Tag.query.filter_by(name=name).first()
                if tag is None:
                    tag = Tag(name=name, slug=slugify(name))
                    db.session.add(tag)
                tags_cache[name] = tag
            tag_objs.append(tags_cache[name])

        slug = unique_slug(
            slugify(entry["title"]),
            lambda s: Post.query.filter_by(slug=s).first() is not None,
        )
        post = Post(
            author_id=author.id,
            title=entry["title"],
            slug=slug,
            excerpt=entry["excerpt"],
            body_source=entry["body_source"],
            body_html=sanitize_html(entry["body_source"]),
            sanitizer_version=SANITIZER_VERSION,
            kind=entry["kind"],
            branch=entry["branch"],
            is_concept=entry["is_concept"],
            tags=tag_objs,
        )
        post.publish()
        db.session.add(post)

    db.session.commit()
    return len(posts_data)


@click.command("seed")
def seed():
    """Dane przykładowe do developmentu — nieprzeznaczone na produkcję."""
    if Post.query.first():
        click.echo("Baza już zawiera wpisy — pomijam.")
        return

    count = _seed_posts()
    if count:
        click.echo(f"Dodano {count} wpisów przykładowych.")


@click.command("reset-demo")
def reset_demo():
    """Czyści treść dodaną w trakcie demo i przywraca seed — wołane co
    godzinę przez cron w kontenerze produkcyjnym trybu demo."""
    from app.demo import reset_demo_content

    reset_demo_content()
    click.echo("Demo zresetowane do stanu początkowego.")


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
