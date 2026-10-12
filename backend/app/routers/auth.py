from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..audit import write_audit
from ..config import settings
from ..db import get_db
from ..deps import client_ip, current_user, require_csrf
from ..models import User, UserSession
from ..rate_limit import allow
from ..schemas import ChangePasswordIn, LoginIn, MeOut
from ..security import DUMMY_HASH, hash_password, hash_token, needs_rehash, new_token, password_problem, verify_password
from ..timeutil import utcnow

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _set_session_cookie(response: Response, token: str, max_age: int) -> None:
    response.set_cookie(
        settings.resolved_cookie_name,
        token,
        max_age=max_age,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        path="/",
    )


@router.post("/login", response_model=MeOut)
async def login(body: LoginIn, request: Request, response: Response, db: Annotated[AsyncSession, Depends(get_db)]):
    ip = client_ip(request) or "unknown"
    if not allow(f"login:{ip}", max_hits=20, window_seconds=300):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many login attempts. Try again later.")

    user = (await db.execute(select(User).where(User.username == body.username.strip().lower()))).scalar_one_or_none()
    now = utcnow()

    if user is None:
        await verify_password(DUMMY_HASH, body.password)  # keep response time constant either way
        await write_audit(db, action="login_failed", username=body.username, ip=ip, detail="unknown user")
        await db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password")

    if user.locked_until and user.locked_until > now:
        wait_min = max(1, int((user.locked_until - now).total_seconds() // 60) + 1)
        raise HTTPException(status.HTTP_423_LOCKED, f"Account locked. Try again in {wait_min} minute(s).")

    ok = await verify_password(user.password_hash, body.password)
    if not ok:
        user.failed_attempts += 1
        if user.failed_attempts >= settings.lockout_threshold:
            user.locked_until = now + timedelta(minutes=settings.lockout_minutes)
            user.failed_attempts = 0
            await write_audit(db, action="account_locked", user=user, ip=ip)
        await write_audit(db, action="login_failed", user=user, ip=ip)
        await db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password")

    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account has been disabled")

    if needs_rehash(user.password_hash):
        user.password_hash = await hash_password(body.password)

    user.failed_attempts = 0
    user.locked_until = None
    user.last_login_at = now

    token = new_token()
    session = UserSession(
        user_id=user.id,
        token_hash=hash_token(token),
        csrf_token=new_token(),
        expires_at=now + timedelta(hours=settings.session_absolute_hours),
        ip=ip,
        user_agent=request.headers.get("user-agent", "")[:300],
    )
    db.add(session)
    await write_audit(db, action="login_succeeded", user=user, ip=ip)
    await db.commit()

    _set_session_cookie(response, token, settings.session_absolute_hours * 3600)
    response.headers["X-CSRF-Token"] = session.csrf_token
    return MeOut(username=user.username, full_name=user.full_name, role=user.role, must_change_password=user.must_change_password)


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_csrf)],
):
    token = request.cookies.get(settings.resolved_cookie_name)
    if token:
        session = (await db.execute(select(UserSession).where(UserSession.token_hash == hash_token(token)))).scalar_one_or_none()
        if session:
            session.revoked_at = utcnow()
    await write_audit(db, action="logout", user=user, ip=client_ip(request))
    await db.commit()
    response.delete_cookie(settings.resolved_cookie_name, path="/")


@router.get("/me", response_model=MeOut)
async def me(user: Annotated[User, Depends(current_user)]):
    return MeOut(username=user.username, full_name=user.full_name, role=user.role, must_change_password=user.must_change_password)


@router.post("/change-password", status_code=204)
async def change_password(
    body: ChangePasswordIn,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_csrf)],
):
    if not await verify_password(user.password_hash, body.current_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Current password is incorrect")
    problem = password_problem(body.new_password, user.username)
    if problem:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, problem)
    user.password_hash = await hash_password(body.new_password)
    user.must_change_password = False
    await write_audit(db, action="password_changed", user=user, ip=client_ip(request))
    await db.commit()
