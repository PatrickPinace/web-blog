# web-blog

[![CI](https://github.com/PatrickPinace/web-blog/actions/workflows/ci.yml/badge.svg)](https://github.com/PatrickPinace/web-blog/actions/workflows/ci.yml)

Autorski blog i portfolio z prywatnym panelem zarządzania treścią. Aplikacja
jest renderowana po stronie serwera we Flasku i pokazuje nie tylko gotowe
wpisy, lecz także proces budowy samego serwisu.

Projekt jest nadal rozwijany. Repozytorium zawiera konfigurację lokalną oraz
obraz Docker, ale nie deklaruje aktualnie publicznego wdrożenia ani konkretnego
dostawcy hostingu.

## Co potrafi aplikacja

### Część publiczna

- strona główna z listą wpisów, paginacją i zachowanymi dawnymi filtrami URL;
- artykuły ze spisem treści, tagami i nawigacją między wpisami;
- ręcznie uporządkowana seria o budowie bloga;
- indeks tagów, wyszukiwanie oraz kanał RSS;
- jasny i ciemny motyw oraz responsywny układ;
- ukrywanie szkiców, wpisów w koszu i publikacji zaplanowanych na przyszłość.

### Panel autora

- konta administratorów tworzone z CLI, bez publicznej rejestracji;
- tworzenie, edycja, podgląd, duplikowanie i publikowanie wpisów;
- szkice, publikacja zaplanowana, kosz z przywracaniem oraz historia operacji;
- edytor Quill, tagi, znaczki i klasyfikacja wpisów;
- upload obrazów do Cloudinary oraz osadzanie filmów YouTube;
- ostrzeżenie przed opuszczeniem formularza z niezapisanymi zmianami.

Harmonogram działa leniwie: wpis po terminie staje się publiczny przy następnym
odczycie publicznej części serwisu. Nie działa tu osobny proces cron. Historia
operacji zapisuje rodzaj zmiany, ale nie przechowuje poprzednich wersji treści.

## Stos

| Warstwa | Technologia |
| --- | --- |
| Backend | Python 3.12, Flask 3 |
| ORM i migracje | SQLAlchemy 2, Alembic / Flask-Migrate |
| Baza | PostgreSQL |
| Szablony | Jinja2, renderowanie po stronie serwera |
| Edytor | Quill, przechowywany lokalnie w repozytorium |
| Sanityzacja | bleach |
| Logowanie | Flask-Login, Argon2, konta tworzone z CLI |
| Obrazy | Cloudinary |
| Serwer WSGI | Gunicorn |

## Uruchomienie lokalne

Wymagania: Python 3.12+, Docker z Docker Compose oraz wolny port 5432.

```bash
git clone https://github.com/PatrickPinace/web-blog.git
cd web-blog

python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt

cp .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"
# Wklej wynik jako SECRET_KEY w .env i uzupełnij branding.

docker compose up -d db
flask db upgrade
flask create-admin
flask run
```

Aplikacja będzie dostępna pod `http://localhost:5000`, a logowanie autora pod
`http://localhost:5000/admin/login`. Kontener Postgresa z
`docker-compose.yml` używa lokalnie danych zgodnych z domyślnym
`DATABASE_URL` z `.env.example`.

Cloudinary jest potrzebne do wysyłania obrazów z pliku. Pozostałe funkcje
blogowe można sprawdzać lokalnie bez wykonywania uploadu.

## Konfiguracja

Skopiuj `.env.example` do `.env`. Nie dodawaj pliku `.env` do repozytorium.

### Aplikacja i dane

| Zmienna | Znaczenie |
| --- | --- |
| `SECRET_KEY` | losowy, prywatny klucz sesji |
| `DATABASE_URL` | adres bazy obsługiwany przez SQLAlchemy; projekt używa sterownika `psycopg` |
| `MAX_UPLOAD_MB` | maksymalny rozmiar requestu z uploadem |
| `ALLOWED_IMAGE_HOSTS` | domeny obrazów wstawianych przez URL, rozdzielone przecinkami |
| `CLOUDINARY_URL` | pełna konfiguracja Cloudinary |
| `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` | alternatywa dla `CLOUDINARY_URL` |

### Branding i odnośniki

| Zmienna | Gdzie jest używana |
| --- | --- |
| `BLOG_TITLE` | nazwa w nagłówku i tytułach stron |
| `BLOG_DESCRIPTION` | domyślny opis strony i RSS |
| `BLOG_AUTHOR` | podpis w stopce i sekcja o autorze |
| `BLOG_BASE_URL` | bezwzględne adresy w RSS |
| `BLOG_EMAIL` | kontakt w stopce i na stronie „O projekcie” |
| `BLOG_GITHUB_URL` | profil GitHub w stopce i na stronie „O projekcie” |
| `BLOG_REPOSITORY_URL` | przycisk „Zobacz kod” na stronie głównej |
| `BLOG_PORTFOLIO_URL` | odnośnik do portfolio |

Puste wartości opcjonalnych linków nie są renderowane. Dzięki temu domyślna
konfiguracja nie tworzy martwych odnośników ani nie podszywa się pod autora.

### Seria o budowie bloga

`BLOG_BUILD_SERIES_SLUGS` jest rozdzieloną przecinkami listą slugów, na przykład:

```dotenv
BLOG_BUILD_SERIES_SLUGS=po-co-zbudowalem-wlasny-blog,jak-zaprojektowalem-czytanie-na-tym-blogu,od-szkicu-do-publikacji
```

Kolejność tej listy steruje spisem na `/about`, odnośnikiem „Zacznij tutaj”
oraz nawigacją „Poprzednia/Następna część”. Wpisz każdy slug tylko raz.
Brakujący wpis, szkic, wpis w koszu i wpis zaplanowany na przyszłość są
pomijane bez ujawniania tytułu. Gdy seria jest pusta, „Zacznij tutaj” prowadzi
do strony „O projekcie”.

## Testy i jakość

Po aktywowaniu środowiska wirtualnego:

```bash
pytest
pytest tests/security
ruff check .
git diff --check
```

Testy korzystają z odseparowanej konfiguracji. W CI uruchamiają się na bazie
`blog_test`; lokalne fixture testowe mogą korzystać z SQLite w pamięci. Nie
ustawiaj `TEST_DATABASE_URL` na bazę zawierającą dane, które chcesz zachować.

Po każdej zmianie whitelisty w `app/utils/sanitize.py` uruchom cały zestaw
testów bezpieczeństwa. Zapisane wpisy przechowują wersję reguł sanityzacji;
po takiej zmianie administrator powinien wykonać:

```bash
flask resanitize
```

## Frontend i dostępność

Frontend nie wymaga osobnego kroku budowania. Style i skrypty są w
`app/static/`, a fonty IBM Plex i Quill są przechowywane lokalnie.

Publiczna nawigacja, treść i odnośniki spisu treści pozostają dostępne bez
JavaScript. Skrypty ulepszają między innymi menu mobilne, zmianę motywu i
podświetlanie spisu; panel używa JavaScriptu do obsługi edytora Quill. Motyw
użytkownika jest zapamiętywany w `localStorage`, a animacje uwzględniają
`prefers-reduced-motion`.

## Bezpieczeństwo treści

- publicznie renderowane HTML przechodzi przez `bleach` z jawną listą tagów,
  atrybutów i klas;
- iframe z treści autora jest odrzucany; zwalidowany link YouTube jest
  zamieniany na osadzenie dopiero podczas renderowania;
- obrazy z URL muszą używać HTTPS i należeć do skonfigurowanej listy domen;
- formularze są chronione przez CSRF, a logowanie ma ograniczenie prób;
- CSP nie dopuszcza skryptów inline, a produkcyjna konfiguracja wymusza HTTPS.

## Wdrożenie

Repozytorium zawiera `Dockerfile`, który uruchamia migracje i Gunicorna na
porcie 8000. Nie jest to deklaracja działającej instancji ani rekomendacja
konkretnego hostingu.

Przed wdrożeniem trzeba samodzielnie wybrać dostawcę aplikacji, PostgreSQL i
magazynu obrazów, sprawdzić ich bieżącą dokumentację, ceny oraz limity, a potem:

1. ustawić produkcyjny `SECRET_KEY`, `DATABASE_URL` i opcjonalnie Cloudinary;
2. uzupełnić prawdziwy branding, kontakt, adres repozytorium i `BLOG_BASE_URL`;
3. wykonać migracje i jednorazowo utworzyć konto przez `flask create-admin`;
4. zweryfikować HTTPS, logowanie, upload, ochronę szkicu, publikację i RSS;
5. skonfigurować trwały backend limitera zamiast magazynu w pamięci procesu.

Aktualne wymagania i sposób konfiguracji wybranego dostawcy należy sprawdzić
w momencie wdrożenia. Projekt nie utrwala w README historycznych cen ani
limitów zewnętrznych usług.

## Licencja

MIT — patrz [LICENSE](LICENSE).
