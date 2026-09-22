#!/bin/sh
# Entrypoint kontenera produkcyjnego. Migracje zawsze, potem dwie ścieżki:
#
# - DEMO_MODE niepusty: konto demo (idempotentnie, patrz create-demo-user),
#   reset bazy co godzinę w tle (prosty sleep-loop, nie osobny serwis cron —
#   ten sam kontener, jeden mniej ruchomych części do popsucia), gunicorn
#   na pierwszym planie.
# - inaczej: zwykły start, bez śladu trybu demo w kodzie/procesach.
set -e

flask db upgrade

if [ -n "$DEMO_MODE" ]; then
  flask create-demo-user
  (
    while true; do
      sleep 3600
      flask reset-demo
    done
  ) &
fi

exec gunicorn --bind 0.0.0.0:8000 --workers 2 --access-logfile - --error-logfile - wsgi:app
