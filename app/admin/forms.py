from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    HiddenField,
    IntegerField,
    PasswordField,
    SelectField,
    SelectMultipleField,
    StringField,
)
from wtforms.validators import DataRequired, Length, Optional

from app.models import Label, Post


class LoginForm(FlaskForm):
    username = StringField("Nazwa użytkownika", validators=[DataRequired()])
    password = PasswordField("Hasło", validators=[DataRequired()])


class PostForm(FlaskForm):
    title = StringField(
        "Tytuł", validators=[DataRequired(), Length(max=200)]
    )
    excerpt = StringField("Krótki opis (excerpt)", validators=[Length(max=500)])
    # Bez DataRequired: pole ma wartość domyślną, a SelectField i tak
    # odrzuci wartość spoza `choices` (walidacja "pre-validate").
    kind = SelectField(
        "Typ wpisu",
        choices=[
            (Post.KIND_CASE_STUDY, "Realizacja"),
            (Post.KIND_NOTE, "Notatka techniczna"),
            (Post.KIND_ESSAY, "Felieton"),
        ],
        default=Post.KIND_CASE_STUDY,
    )
    branch = StringField(
        "Branża", validators=[Optional(), Length(max=80)]
    )
    is_concept = BooleanField("Projekt koncepcyjny (fikcyjny klient)")
    labels = SelectMultipleField("Znaczki", coerce=int, validators=[Optional()])
    status = SelectField(
        "Status",
        choices=[
            (Post.STATUS_DRAFT, "Szkic"),
            (Post.STATUS_PUBLISHED, "Opublikowany"),
        ],
        validators=[DataRequired()],
    )
    tags = StringField(
        "Tagi (oddzielone przecinkiem)", validators=[Length(max=300)]
    )
    # Surowy HTML z edytora Quill. Sanityzacja (bleach) dzieje się w widoku,
    # NIGDY tutaj — walidator formularza nie jest miejscem na bezpieczeństwo
    # treści, bo łatwo o nim zapomnieć przy zmianie formularza.
    body_source = HiddenField("Treść")


class DeletePostForm(FlaskForm):
    """Pusty formularz — wymuszamy CSRF na usuwaniu, jak każda destrukcyjna akcja."""

    pass


class PostStatusForm(FlaskForm):
    """Pusty formularz — CSRF na przełączniku statusu z listy wpisów."""

    pass


class LabelForm(FlaskForm):
    name = StringField("Nazwa", validators=[DataRequired(), Length(max=40)])
    color = SelectField(
        "Kolor",
        choices=[(c, c) for c in Label.COLORS],
        default=Label.DEFAULT_COLOR,
    )


class DeleteLabelForm(FlaskForm):
    """Pusty formularz — wymuszamy CSRF na usuwaniu, jak każda destrukcyjna akcja."""

    pass


class RenameTagForm(FlaskForm):
    name = StringField("Nazwa", validators=[DataRequired(), Length(max=80)])


class MergeTagsForm(FlaskForm):
    # source znika, wszystkie jego wpisy przechodzą na target — kolejność
    # w formularzu (source, target) musi być czytelna dla użytkownika,
    # bo to operacja nieodwracalna.
    source_id = IntegerField(validators=[DataRequired()])
    target_id = IntegerField(validators=[DataRequired()])


class DeleteTagForm(FlaskForm):
    """Pusty formularz — wymuszamy CSRF na usuwaniu, jak każda destrukcyjna akcja."""

    pass
