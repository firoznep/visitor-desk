import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..audit import write_audit
from ..db import get_db
from ..deps import client_ip, require_csrf, require_role
from ..models import AuditLog, Company, Department, User, UserSession
from ..schemas import AuditOut, NameOptionCreateIn
from ..security import hash_password, password_problem
from ..timeutil import utcnow

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_role("admin"))])


class DepartmentOut(BaseModel):
    name: str


@router.post("/departments", response_model=DepartmentOut, status_code=201)
async def create_department(
    body: NameOptionCreateIn,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(require_csrf)],
):
    name = body.name.strip()
    exists = (await db.execute(select(Department.id).where(func.lower(Department.name) == name.lower()))).first()
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "Department already exists")
    department = Department(name=name)
    db.add(department)
    await write_audit(db, action="department_created", user=admin, target=name, ip=client_ip(request))
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Department already exists") from exc
    return DepartmentOut(name=department.name)


@router.post("/companies", response_model=DepartmentOut, status_code=201)
async def create_company(
    body: NameOptionCreateIn,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(require_csrf)],
):
    name = body.name.strip()
    exists = (await db.execute(select(Company.id).where(func.lower(Company.name) == name.lower()))).first()
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "Company already exists")
    company = Company(name=name)
    db.add(company)
    await write_audit(db, action="company_created", user=admin, target=name, ip=client_ip(request))
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Company already exists") from exc
    return DepartmentOut(name=company.name)


@router.get("/audit", response_model=list[AuditOut])
async def list_audit(db: Annotated[AsyncSession, Depends(get_db)], limit: int = Query(default=200, ge=1, le=1000)):
    rows = (await db.execute(select(AuditLog).order_by(AuditLog.at.desc()).limit(limit))).scalars().all()
    return [AuditOut(at=r.at, username=r.username, action=r.action, target=r.target, detail=r.detail) for r in rows]


class UserOut(BaseModel):
    id: uuid.UUID
    username: str
    full_name: str
    role: str
    is_active: bool
    must_change_password: bool


class CreateUserIn(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[a-z0-9._-]+$")
    full_name: str = Field(min_length=2, max_length=80)
    role: str
    temporary_password: str = Field(min_length=12, max_length=128)

    @field_validator("role")
    @classmethod
    def _role(cls, v: str) -> str:
        if v not in ("receptionist", "admin"):
            raise ValueError("role must be 'receptionist' or 'admin'")
        return v


class ResetPasswordIn(BaseModel):
    temporary_password: str = Field(min_length=12, max_length=128)


@router.get("/users", response_model=list[UserOut])
async def list_users(db: Annotated[AsyncSession, Depends(get_db)]):
    rows = (await db.execute(select(User).order_by(User.created_at))).scalars().all()
    return [UserOut(id=u.id, username=u.username, full_name=u.full_name, role=u.role, is_active=u.is_active, must_change_password=u.must_change_password) for u in rows]


@router.post("/users", response_model=UserOut, status_code=201)
async def create_user(
    body: CreateUserIn,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(require_csrf)],
):
    username = body.username.lower()
    exists = (await db.execute(select(User.id).where(User.username == username))).first()
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "Username already exists")
    problem = password_problem(body.temporary_password, username)
    if problem:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, problem)
    user = User(
        username=username, full_name=body.full_name, role=body.role,
        password_hash=await hash_password(body.temporary_password), must_change_password=True,
    )
    db.add(user)
    await write_audit(db, action="user_created", user=admin, target=username, detail=f"role={body.role}", ip=client_ip(request))
    await db.commit()
    return UserOut(id=user.id, username=user.username, full_name=user.full_name, role=user.role, is_active=user.is_active, must_change_password=True)


@router.post("/users/{user_id}/reset-password", status_code=204)
async def reset_user_password(
    user_id: uuid.UUID,
    body: ResetPasswordIn,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(require_csrf)],
):
    if admin.id == user_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot reset your own password here")
    target = await db.get(User, user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    problem = password_problem(body.temporary_password, target.username)
    if problem:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, problem)

    now = utcnow()
    target.password_hash = await hash_password(body.temporary_password)
    target.must_change_password = True
    target.failed_attempts = 0
    target.locked_until = None
    await db.execute(
        update(UserSession)
        .where(UserSession.user_id == target.id, UserSession.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    await write_audit(
        db,
        action="user_password_reset",
        user=admin,
        target=target.username,
        ip=client_ip(request),
    )
    await db.commit()


@router.post("/users/{user_id}/disable", status_code=204)
async def disable_user(
    user_id: str,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(require_csrf)],
):
    if str(admin.id) == user_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot disable your own account")
    target = await db.get(User, user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    target.is_active = False
    await write_audit(db, action="user_disabled", user=admin, target=target.username, ip=client_ip(request))
    await db.commit()


@router.post("/users/{user_id}/enable", status_code=204)
async def enable_user(
    user_id: uuid.UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(require_csrf)],
):
    target = await db.get(User, user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    target.is_active = True
    await write_audit(db, action="user_enabled", user=admin, target=target.username, ip=client_ip(request))
    await db.commit()
