# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    FLASK_APP=wsgi.py \
    FLASK_ENV=production

WORKDIR /app

# Zależności w osobnej warstwie — cache Dockera nie inwaliduje się przy
# każdej zmianie kodu aplikacji, tylko gdy zmienia się requirements.txt.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Bez rootowego użytkownika w kontenerze produkcyjnym.
RUN useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Migracje przy starcie kontenera, potem gunicorn. Bezpieczne przy wielu
# instancjach na raz — Alembic blokuje tabelę wersji na czas migracji
# (na Koyeb free tier jest jedna instancja, więc i tak bez znaczenia).
CMD ["sh", "-c", "flask db upgrade && gunicorn --bind 0.0.0.0:8000 --workers 2 --access-logfile - --error-logfile - wsgi:app"]
