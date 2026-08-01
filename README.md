# web-blog

Blog z panelem administracyjnym — Flask + PostgreSQL, renderowany po stronie
serwera, z edytorem WYSIWYG i uploadem obrazków.

Projekt jest jednocześnie **działającym blogiem** i **template'em do reużycia**:
konfiguracja przez zmienne środowiskowe, branding w jednym miejscu, instrukcja
forka poniżej.

> 🚧 **Status: w budowie.** Etap 0 z 8 (setup repozytorium).
> Live URL pojawi się tutaj po wdrożeniu.

---

## Stack

| Warstwa | Technologia |
|---|---|
| Backend | Python 3.12, Flask 3 |
| ORM / migracje | SQLAlchemy 2, Alembic |
| Baza | PostgreSQL |
| Szablony | Jinja2 (server-side) |
| Edytor | Quill (WYSIWYG) |
| Sanityzacja | bleach |
| Auth | Flask-Login (jedno konto admina) |
| Obrazki | Cloudinary |
| Serwer WSGI | Gunicorn |

---

## Funkcje

**Część publiczna** — lista wpisów z paginacją, widok wpisu, filtrowanie po
tagach, RSS, własne strony błędów.

**Panel admina** (`/admin`) — CRUD wpisów, edytor wizualny, upload obrazków,
tagi, statusy draft/published, podgląd szkicu przed publikacją.

---

## Uruchomienie lokalne

Wymagania: Python 3.12+, Docker (dla bazy).

```bash
# 1. Repozytorium
git clone https://github.com/PatrickPinace/web-blog.git
cd web-blog

# 2. Środowisko wirtualne
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Zależności (wariant deweloperski, z testami i linterem)
pip install -r requirements-dev.txt

# 4. Konfiguracja
cp .env.example .env
# Wygeneruj SECRET_KEY i wklej do .env:
python -c "import secrets; print(secrets.token_hex(32))"

# 5. Baza danych — Postgres w kontenerze
docker compose up -d db

# 6. Migracje i konto administratora
flask db upgrade
flask create-admin

# 7. Start
flask run
```

Aplikacja: http://localhost:5000 · panel: http://localhost:5000/admin

Lokalnie używamy Postgresa, nie SQLite — parytet z produkcją od pierwszego dnia.

---

## Testy

```bash
pytest                     # całość
pytest tests/security      # tylko testy bezpieczeństwa
ruff check .               # lint
```

`tests/security/` jest wydzielone celowo — te testy uruchamiamy **po każdej
zmianie whitelisty sanitizera**, niezależnie od reszty prac.

---

## Fork — jak zrobić z tego swój blog

1. Zrób fork i sklonuj repozytorium.
2. Ustaw w `.env`: `BLOG_TITLE`, `BLOG_DESCRIPTION`, `BLOG_AUTHOR`,
   `BLOG_BASE_URL`.
3. Podmień kolory i typografię w `app/static/css/style.css` (zmienne CSS
   na górze pliku).
4. Załóż darmowe konta: [Neon](https://neon.tech) (baza),
   [Cloudinary](https://cloudinary.com) (obrazki),
   [Koyeb](https://koyeb.com) (hosting).
5. Wdróż zgodnie z sekcją poniżej.

Branding jest wyciągnięty do konfiguracji — nie trzeba grzebać w szablonach.

---

## Wdrożenie

Docelowo: **Koyeb** (aplikacja) + **Neon** (Postgres) + **Cloudinary**
(obrazki) — w całości na darmowych planach.

Zmienne środowiskowe na produkcji: `DATABASE_URL`, `SECRET_KEY`,
`CLOUDINARY_URL`, `FLASK_ENV=production`.

Szczegółowa instrukcja pojawi się po etapie 6.

### Uwaga o pierwszym wejściu

Blog działa na darmowym hostingu, który usypia instancję po godzinie bez
ruchu. Pierwsze wejście po przerwie może trwać kilkanaście sekund — to
normalne zachowanie, nie awaria.

---

## Monitorowanie zużycia

Limity darmowych planów warto sprawdzać raz na jakiś czas:

| Usługa | Limit | Gdzie sprawdzić |
|---|---|---|
| Neon | 100 CU-godzin/mies., 0.5 GB storage | Panel Neona → Usage |
| Cloudinary | 25 kredytów/mies. (storage + transfer + transformacje łącznie) | Dashboard → Usage |
| Koyeb | 1 instancja free, scale-to-zero po 1 h | Panel Koyeb → Metrics |

Obrazki serwujemy z transformacjami `f_auto,q_auto` (automatyczny WebP
i kompresja), co znacząco ogranicza zużycie kredytów Cloudinary.

---

## Bezpieczeństwo

Edytor WYSIWYG oznacza przyjmowanie HTML od użytkownika, dlatego:

- treść przechodzi przez `bleach` z jawną whitelistą tagów i atrybutów,
- atrybut `class` jest filtrowany **po wartości** — przechodzą wyłącznie
  klasy `ql-*` generowane przez edytor,
- `<iframe>` **nie jest** dopuszczony w treści; embed YouTube powstaje po
  stronie serwera z zwalidowanego URL-a,
- `img src` akceptowany tylko z whitelisty domen, bez pobierania zasobu
  przez serwer,
- CSRF na wszystkich formularzach, rate limiting na logowaniu, nagłówki
  bezpieczeństwa przez Flask-Talisman.

Zmiana reguł sanityzacji wymaga uruchomienia `flask resanitize` — zapisane
wpisy przechowują wersję reguł, którymi zostały przetworzone.

---

## Licencja

MIT — patrz [LICENSE](LICENSE).
