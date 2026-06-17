#!/bin/sh
set -e

echo '[entrypoint] Aguardando PostgreSQL...'
python - <<'PY'
import os
import time

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import connections
from django.db.utils import OperationalError

conn = connections['default']
for _ in range(60):
    try:
        conn.ensure_connection()
        print('[entrypoint] PostgreSQL disponível.')
        break
    except OperationalError:
        print('[entrypoint] Aguardando PostgreSQL...')
        time.sleep(2)
else:
    raise SystemExit('[entrypoint] PostgreSQL indisponível após 120s.')
PY

echo '[entrypoint] Aplicando migrations...'
python manage.py migrate --noinput

echo '[entrypoint] Coletando estáticos...'
python manage.py collectstatic --noinput --clear

# Superuser opcional e idempotente (createsuperuser ignora se o e-mail já existe).
if [ -n "$DJANGO_SUPERUSER_EMAIL" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
    echo '[entrypoint] Garantindo superuser...'
    python manage.py createsuperuser --noinput \
        --email "$DJANGO_SUPERUSER_EMAIL" \
        --nome_completo "${DJANGO_SUPERUSER_NOME_COMPLETO:-Administrador}" \
        2>/dev/null \
        && echo '[entrypoint] Superuser criado.' \
        || echo '[entrypoint] Superuser já existe ou criação ignorada.'
fi

echo '[entrypoint] Iniciando aplicação.'
exec "$@"
