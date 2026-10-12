#!/usr/bin/env python3
r"""Decrypt visitor ID numbers and dates of birth from a Visitor Desk database (backup or live).

Why this exists
---------------
Visitor ID numbers and dates of birth are stored encrypted (AES-256-GCM) so that a stolen
database file or backup is not enough to read them. This script is the *other half*: given
the encryption keys, it decrypts a table straight from Postgres or from a plain CSV export,
with NO dependency on the FastAPI app, the React frontend, or any of this project's Python
packages other than `cryptography` and (optionally) `psycopg2` if you point it at a live
database instead of a CSV.

This means: even years from now, even if this whole codebase is gone, anyone who has this
one file and the key can still read the data. That is deliberate -- your backups must never
become unreadable because "the app" changed.

Typical use, restoring an encrypted daily backup for an audit:

    # 1. Restore the .sql.gz backup into a scratch Postgres database (any host is fine):
    createdb visitors_restore
    gunzip -c visitors_2026-09-29.sql.gz | psql visitors_restore

    # 2. Export just the columns you need, still encrypted, to CSV:
    psql visitors_restore -c "\copy (select id, id_number_enc, id_number_hash, dob_enc from visits) to 'visits_enc.csv' with csv header"

    # 3. Decrypt that CSV with the real key (kept in your secrets manager, NOT in this repo):
    python3 decrypt_export.py --csv visits_enc.csv --keys "k1:<base64-key>" --out visits_decrypted.csv

Or skip the CSV step and point it straight at a live/restored database:

    python3 decrypt_export.py --db "postgresql://readonly_user:pw@localhost/visitors_restore" \
        --keys "k1:<base64-key>,k0:<old-base64-key>" --out visits_decrypted.csv

The output CSV contains plaintext personal data. Treat it like any other unencrypted
export: decrypt on a machine you trust, share the file only over an encrypted channel,
and delete it once you are done with it.

Key management
---------------
- The key(s) are the SAME "ID_ENCRYPTION_KEYS" value from the API's .env file (or the
  specific key id you need, if you have rotated keys and are reading an old backup).
  Format: "k1:<b64>,k0:<b64>" -- you can pass just the one key id you need.
- This script decrypts ID numbers and dates of birth. It does NOT need the ID_INDEX_KEY
  (that key only supports duplicate-visitor lookups, never decryption).
- Never store the key in this script, in your shell history (use a keys file, see
  --keys-file), or in the same place as the backup itself.
"""
import argparse
import base64
import csv
import getpass
import sys
from pathlib import Path

try:
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except ImportError:
    sys.exit("Missing dependency. Install with:  pip install cryptography")


def b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def parse_keys(spec: str) -> dict[str, bytes]:
    keys: dict[str, bytes] = {}
    for part in spec.split(","):
        kid, _, val = part.strip().partition(":")
        if not kid or not val:
            raise ValueError(f"Bad --keys entry: {part!r}. Expected format 'k1:<base64-key>'.")
        key = b64d(val)
        if len(key) != 32:
            raise ValueError(f"Key '{kid}' decodes to {len(key)} bytes, expected 32.")
        keys[kid] = key
    return keys


def decrypt(token: str, keys: dict[str, bytes], aad: bytes) -> str:
    """token format: '<key_id>.<base64url(12-byte nonce || ciphertext+tag)>'"""
    kid, _, payload = token.partition(".")
    key = keys.get(kid)
    if key is None:
        raise KeyError(f"No key provided for key id '{kid}'. Pass it via --keys, e.g. '{kid}:<base64-key>,...'")
    raw = b64d(payload)
    nonce, ct = raw[:12], raw[12:]
    return AESGCM(key).decrypt(nonce, ct, aad).decode()


def load_rows_from_csv(path: str):
    with open(path, newline="") as f:
        yield from csv.DictReader(f)


def load_rows_from_db(url: str):
    try:
        import psycopg2
        import psycopg2.extras
    except ImportError:
        sys.exit("Reading from a live database needs psycopg2. Install with:  pip install psycopg2-binary\n"
                  "Or export to CSV with \\copy first (see --csv, and the docstring above).")
    conn = psycopg2.connect(url)
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT id, badge_no, full_name, id_number_enc, dob_enc FROM visits ORDER BY created_at")
            yield from cur
    finally:
        conn.close()


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--csv", help="CSV exported from the visits table (must include: id, id_number_enc, dob_enc)")
    src.add_argument("--db", help="Postgres connection URL to read the visits table directly (read-only user recommended)")
    p.add_argument("--keys", help="Encryption keys, e.g. 'k1:<base64>,k0:<base64>'. Omit to be prompted (safer: keeps it out of shell history).")
    p.add_argument("--keys-file", help="Path to a file containing the --keys value, instead of passing it on the command line.")
    p.add_argument("--out", required=True, help="Where to write the decrypted CSV")
    args = p.parse_args()

    if args.keys_file:
        keys_spec = Path(args.keys_file).read_text().strip()
    elif args.keys:
        keys_spec = args.keys
    else:
        keys_spec = getpass.getpass("Encryption keys (k1:<base64>,k0:<base64>): ").strip()

    keys = parse_keys(keys_spec)
    rows = load_rows_from_csv(args.csv) if args.csv else load_rows_from_db(args.db)

    written, failed = 0, 0
    with open(args.out, "w", newline="") as out_f:
        writer = None
        for row in rows:
            row_id = row["id"]
            try:
                id_number = decrypt(row["id_number_enc"], keys, f"visits:id_number:{row_id}".encode())
                dob = decrypt(row["dob_enc"], keys, f"visits:dob:{row_id}".encode())
                status = "ok"
            except (InvalidTag, ValueError, KeyError) as exc:
                id_number, dob, status = "", "", f"DECRYPT_FAILED: {exc}"
                failed += 1
            out_row = {
                "id": row_id, "badge_no": row.get("badge_no", ""), "full_name": row.get("full_name", ""),
                "id_number": id_number, "date_of_birth": dob, "status": status,
            }
            if writer is None:
                writer = csv.DictWriter(out_f, fieldnames=list(out_row))
                writer.writeheader()
            writer.writerow(out_row)
            written += 1

    print(f"Wrote {written} row(s) to {args.out} ({failed} failed to decrypt).")
    if failed:
        print("Rows that failed usually mean the wrong key id, or a key id missing from --keys.")


if __name__ == "__main__":
    main()
