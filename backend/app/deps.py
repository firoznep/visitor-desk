from datetime import timedelta
from typing import Annotated

from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .db import get_db
from .models import User, UserSession
from .security import hash_token
from .timeutil import utcnow


async def get_session(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    session_cookie: Annotated[str | None, Cookie(alias=None)] = None,
) -> tuple[UserSession, User]:
    token = request.cookies.get(settings.resolved_cookie_name)
    unauthorized = HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    if not token:
        raise unauthorized

    row = (
        await db.execute(
            select(UserSession, User)
            .join(User, User.id == UserSession.user_id)
            .where(UserSession.token_hash == hash_token(token))
        )
    ).first()
    if row is None:
        raise unauthorized
    session, user = row

    now = utcnow()
    if session.revoked_at is not None or session.expires_at < now or not user.is_active:
        raise unauthorized
    if session.last_seen_at + timedelta(minutes=settings.session_idle_minutes) < now:
        session.revoked_at = now
        await db.commit()
        raise unauthorized

    session.last_seen_at = now
    await db.commit()
    return session, user


async def current_user(session_and_user: Annotated[tuple[UserSession, User], Depends(get_session)]) -> User:
    return session_and_user[1]


async def require_csrf(
    request: Request,
    session_and_user: Annotated[tuple[UserSession, User], Depends(get_session)],
    x_csrf_token: Annotated[str | None, Header()] = None,
) -> User:
    """Double-submit CSRF check for the cookie-based session, required on every state-changing request."""
    session, user = session_and_user
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return user
    if not x_csrf_token or x_csrf_token != session.csrf_token:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Missing or invalid CSRF token")
    return user


def require_role(*roles: str):
    async def _check(user: Annotated[User, Depends(require_csrf)]) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not have access to this action")
        return user

    return _check


def client_ip(request: Request) -> str | None:
    # Set real_ip_header in nginx (X-Forwarded-For) and trust only the proxy hop.
    fwd = request.headers.get("x-forwarded-for")
    return fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else None)
