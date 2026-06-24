#!/bin/sh
# Backup do Postgres + media pública/protegida do ProfessorDash.
#
# No Easypanel, o caminho mais simples é habilitar o backup automático do
# service Postgres pelo próprio painel. Este script é alternativa / complemento
# para rodar via cron na VPS (host) ou dentro de um container com acesso ao db.
#
# Uso (exemplos):
#   DATABASE_URL=postgres://user:senha@host:5432/db ./scripts/backup.sh
#   BACKUP_DIR=/srv/backups RETENTION_DAYS=14 ./scripts/backup.sh
set -e

BACKUP_DIR="${BACKUP_DIR:-/srv/professordash/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
PUBLIC_MEDIA_DIR="${PUBLIC_MEDIA_DIR:-/app/media}"
PROTECTED_MEDIA_DIR="${PROTECTED_MEDIA_DIR:-/app/protected_media}"
STAMP="$(date +%Y%m%d-%H%M%S)"

mkdir -p "$BACKUP_DIR"

if [ -z "$DATABASE_URL" ]; then
    echo '[backup] DATABASE_URL ausente.' >&2
    exit 1
fi

echo "[backup] Dump do Postgres -> db-$STAMP.sql.gz"
pg_dump "$DATABASE_URL" | gzip > "$BACKUP_DIR/db-$STAMP.sql.gz"

if [ -d "$PUBLIC_MEDIA_DIR" ]; then
    echo "[backup] Tar da media pública -> media-public-$STAMP.tar.gz"
    tar -czf "$BACKUP_DIR/media-public-$STAMP.tar.gz" -C "$PUBLIC_MEDIA_DIR" .
fi

if [ -d "$PROTECTED_MEDIA_DIR" ]; then
    echo "[backup] Tar da media protegida -> media-protected-$STAMP.tar.gz"
    tar -czf "$BACKUP_DIR/media-protected-$STAMP.tar.gz" -C "$PROTECTED_MEDIA_DIR" .
fi

echo "[backup] Rotação: removendo arquivos > $RETENTION_DAYS dias"
find "$BACKUP_DIR" -name 'db-*.sql.gz' -mtime +"$RETENTION_DAYS" -delete
find "$BACKUP_DIR" -name 'media-public-*.tar.gz' -mtime +"$RETENTION_DAYS" -delete
find "$BACKUP_DIR" -name 'media-protected-*.tar.gz' -mtime +"$RETENTION_DAYS" -delete

echo '[backup] Concluído.'
