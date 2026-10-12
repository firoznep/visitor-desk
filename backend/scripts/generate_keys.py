"""Prints fresh secrets for the .env file. Run once during setup, then store the output in a
password manager or secrets vault -- never commit it."""
import secrets

from app.crypto import generate_key

print(f"ID_ENCRYPTION_KEYS=k1:{generate_key()}")
print("ID_ACTIVE_KEY_ID=k1")
print(f"ID_INDEX_KEY={generate_key()}")
print(f"SCAN_TOKEN_SECRET={secrets.token_urlsafe(48)}")
