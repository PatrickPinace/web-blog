# web-blog

[![CI](https://github.com/PatrickPinace/web-blog/actions/workflows/ci.yml/badge.svg)](https://github.com/PatrickPinace/web-blog/actions/workflows/ci.yml)

Blog z panelem administracyjnym — Flask + PostgreSQL, renderowany po stronie
serwera, z edytorem WYSIWYG i uploadem obrazków.

Projekt jest jednocześnie **działającym blogiem** i **template'em do reużycia**:
konfiguracja przez zmienne środowiskowe, branding w jednym miejscu, instrukcja
forka poniżej.

> 🚧 **Status: w budowie.** Backend, panel i warstwa wizualna gotowe.
> Konfiguracja deployu (etap 6) opisana poniżej — pozostaje samo wdrożenie.
> Live URL pojawi się tutaj po pierwszym deployu.

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
3. Podmień kolory w `app/static/css/style.css` — akcent i cała paleta siedzą
   w zmiennych `:root` (oraz `html[data-theme="dark"]`) na górze pliku.
4. Załóż darmowe konta: [Neon](https://neon.tech) (baza),
   [Cloudinary](https://cloudinary.com) (obrazki),
   [Koyeb](https://koyeb.com) (hosting).
5. Wdróż zgodnie z sekcją poniżej.

Branding jest wyciągnięty do konfiguracji — nie trzeba grzebać w szablonach.

---

## Wdrożenie

**Koyeb** (aplikacja) + **Neon** (Postgres) + **Cloudinary** (obrazki) —
w całości na darmowych planach. Uzasadnienie tej kombinacji zamiast
oczywistego "Render" czy "Fly.io" jest w `workdir/plan.md`, sekcja 3
(skrót: darmowa baza na Renderze wygasa po 30 dniach, Fly.io nie ma już
darmowego tieru dla nowych kont).

### 1. Baza danych — Neon

1. Załóż konto na [neon.tech](https://neon.tech), utwórz projekt.
2. Skopiuj connection string z zakładki *Connection Details* — wygląda jak
   `postgresql://user:pass@ep-xxx.neon.tech/dbname?sslmode=require`.
3. Dopisz do niego sterownik, żeby pasował do naszej konfiguracji:
   `postgresql://` → `postgresql+psycopg://` (patrz `.env.example`).

### 2. Obrazki — Cloudinary

1. Załóż konto na [cloudinary.com](https://cloudinary.com).
2. Na Dashboardzie skopiuj **API Environment variable** (`CLOUDINARY_URL`) —
   gotowy do wklejenia bez edycji.

### 3. Aplikacja — Koyeb

1. Załóż konto na [koyeb.com](https://koyeb.com), połącz z GitHubem.
2. Utwórz Web Service z tego repozytorium, branch `main`. Koyeb wykryje
   `Dockerfile` automatycznie (builder: Dockerfile).
3. Port aplikacji: `8000` (ustawiony w Dockerfile przez `EXPOSE` i w
   komendzie startowej gunicorna).
4. Zmienne środowiskowe (zakładka *Environment variables*):

   | Zmienna | Wartość |
   |---|---|
   | `SECRET_KEY` | `python -c "import secrets; print(secrets.token_hex(32))"` |
   | `DATABASE_URL` | connection string z Neona (z `postgresql+psycopg://`) |
   | `CLOUDINARY_URL` | z Dashboardu Cloudinary |
   | `BLOG_TITLE`, `BLOG_DESCRIPTION`, `BLOG_AUTHOR` | wg własnego brandingu |
   | `BLOG_BASE_URL` | finalny URL z Koyeb, np. `https://xxx.koyeb.app` |

   `FLASK_ENV=production` jest już ustawione na stałe w Dockerfile — nie
   trzeba go dodawać ręcznie.
5. Deploy. Migracje (`flask db upgrade`) uruchamiają się automatycznie przy
   starcie kontenera — patrz `CMD` w `Dockerfile`.

### 4. Konto administratora

Jednorazowo, przez konsolę Koyeb (zakładka *Instances* → *Exec* na żywej
instancji, albo `koyeb service exec`):

```bash
flask create-admin
```

### 5. Weryfikacja po wdrożeniu

- [ ] Strona główna ładuje się po HTTPS
- [ ] `/admin/login` działa, logowanie ustawionym kontem przechodzi
- [ ] Utworzenie draftu → sprawdzić, że `/post/<slug>` zwraca 404
- [ ] Publikacja wpisu → widoczny publicznie
- [ ] Cold start: odczekać >1h bez ruchu, zmierzyć czas pierwszego wejścia

### Jeśli Koyeb zażąda karty płatniczej

Plan B: **Render** (Web Service, free tier) zamiast Koyeba, baza zostaje na
Neonie (nie na wygasającej po 30 dniach bazie Rendera). Reszta konfiguracji
bez zmian — Dockerfile jest przenośny między hostingami.

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

## Front

Bez frameworka i bez kroku budowania — jeden arkusz `style.css` i dwa małe
pliki JS. Kilka rzeczy wynika wprost z polityki bezpieczeństwa:

- **Fonty hostowane lokalnie** (`app/static/fonts/`, IBM Plex, 12 plików
  woff2). CSP ma `default-src 'self'`, więc Google Fonts wymagałoby
  rozluźnienia polityki — a przy okazji nie wysyłamy IP czytelników na
  zewnątrz. Uwaga przy podmianie fontu: polskie znaki są rozbite między
  podzbiory `latin` i `latin-ext` (`ó` jest w tym pierwszym), potrzebne są
  oba.
- **Zero skryptów inline i atrybutów `on*`** — `script-src 'self'` bez
  `unsafe-inline` oznacza, że taki kod po prostu się nie wykona. Stąd np.
  potwierdzenie usuwania wpisu siedzi w `admin-confirm.js`, a nie
  w `onsubmit`.
- **JS jest opcjonalny.** Motyw, spis treści i animacje wejścia to dodatki;
  treść, nawigacja i formularze działają bez nich.
- Motyw jasny/ciemny idzie za ustawieniem systemu, z ręcznym przełącznikiem
  zapamiętywanym w `localStorage`.

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
