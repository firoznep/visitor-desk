"""Creates the first admin user. Run once after migrations, then delete/rotate the printed password.

Usage:  python -m scripts.seed_admin --username admin --full-name "Front Office Admin"
"""
import argparse
import asyncio
import secrets
import sys

sys.path.insert(0, ".")

from sqlalchemy import select

from app.db import SessionLocal
from app.models import User
from app.security import hash_password


async def main(username: str, full_name: str, role: str) -> None:
    async with SessionLocal() as db:
        existing = (await db.execute(select(User).where(User.username == username))).scalar_one_or_none()
        if existing:
            print(f"User '{username}' already exists.")
            return
        temp_password = secrets.token_urlsafe(15)
        db.add(User(username=username, full_name=full_name, role=role, password_hash=await hash_password(temp_password), must_change_password=True))
        await db.commit()
        print(f"Created {role} '{username}'.\nTemporary password: {temp_password}\n"
              "Give this to them over a secure channel; they must change it on first login.")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--username", required=True)
    p.add_argument("--full-name", required=True)
    p.add_argument("--role", default="admin", choices=["admin", "receptionist"])
    args = p.parse_args()
    asyncio.run(main(args.username.lower(), args.full_name, args.role))
