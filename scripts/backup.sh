#!/usr/bin/env bash
# Daily/weekly Postgres backup: dumps, compresses, then encrypts the dump itself with GPG
# so the backup file is safe to copy off-site even though the database columns are already
# encrypted (defence in depth: this also protects usernames, password hashes, audit logs, etc).
#
# Run via cron, e.g.:  0 2 * * * /opt/visitor-desk/scripts/backup.sh >> /var/log/visitor-backup.log 2>&1
#
# Restoring:
#   gpg --decrypt visitors_2026-09-29.sql.gz.gpg > visitors_2026-09-29.sql.gz
#   gunzip -c visitors_2026-09-29.sql.gz | psql "$DATABASE_URL"
# Then, to read visitor personal data from the restore, use decrypt_export.py -- the SQL
# dump alone is still encrypted at the column level.
set -euo pipefail

: "${PGHOST:?set PGHOST}"; : "${PGDATABASE:?set PGDATABASE}"; : "${PGUSER:?set PGUSER}"
: "${BACKUP_DIR:=/var/backups/visitor-desk}"
: "${GPG_RECIPIENT:?set GPG_RECIPIENT to the backup encryption key's email/fingerprint}"
: "${RETENTION_DAYS:=35}"

mkdir -p "$BACKUP_DIR"
stamp="$(date +%F_%H%M)"
dump_file="$BACKUP_DIR/visitors_${stamp}.sql.gz"
enc_file="${dump_file}.gpg"

pg_dump --format=plain --no-owner --no-privileges | gzip -9 > "$dump_file"
gpg --yes --batch --recipient "$GPG_RECIPIENT" --trust-model always --output "$enc_file" --encrypt "$dump_file"
shred -u "$dump_file" 2>/dev/null || rm -f "$dump_file"   # never leave an unencrypted dump on disk

find "$BACKUP_DIR" -name '*.sql.gz.gpg' -mtime +"$RETENTION_DAYS" -delete

echo "Backup written: $enc_file"
echo "Copy it off this host (S3, another site, etc). Only people holding the GPG private key can open it."
