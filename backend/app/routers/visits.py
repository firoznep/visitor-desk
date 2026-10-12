from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..audit import write_audit
from ..crypto import aad, get_vault
from ..db import get_db
from ..deps import client_ip, current_user, require_csrf, require_role
from ..idparse import parse_id
from ..models import Company, Department, User, Visit
from ..schemas import DeleteVisitIn, ManualIdIn, ScanIn, ScanOut, VisitCreateIn, VisitListOut, VisitOut, VisitStatsOut
from ..security import make_scan_token, read_scan_token
from ..timeutil import local_today, utcnow

router = APIRouter(prefix="/api/visits", tags=["visits"])


def _to_out(v: Visit) -> VisitOut:
    return VisitOut(
        id=v.id, badge_no=v.badge_no, visit_date=v.visit_date, full_name=v.full_name, id_last4=v.id_last4,
        nationality=v.nationality, gender=v.gender, id_expiry=v.id_expiry, id_expired=v.id_expired,
        floor=v.floor, purpose=v.purpose, host_name=v.host_name, department=v.department, phone=v.phone,
        company=v.company, vehicle_plate=v.vehicle_plate, notes=v.notes, checked_in_at=v.checked_in_at,
        checked_out_at=v.checked_out_at, is_deleted=v.deleted_at is not None, deleted_by=v.deleted_by,
    )


@router.post("/scan", response_model=ScanOut)
async def scan(
    body: ScanIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(current_user)],
):
    """Parses the raw scan on the server (never trust client-parsed ID fields) and hands back a
    short-lived signed token. The create-visit step only accepts data that round-trips through
    this token, so a receptionist's browser cannot invent or edit identity fields."""
    try:
        parsed = parse_id(body.raw)
    except ValueError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Couldn't read this ID. Scan again or check the barcode is clean.")

    vault = get_vault()
    id_hash = vault.blind_index(parsed.id_number)
    already = (
        await db.execute(
            select(Visit.id).where(
                Visit.id_number_hash == id_hash,
                Visit.visit_date == local_today(),
                Visit.checked_out_at.is_(None),
                Visit.deleted_at.is_(None),
            )
        )
    ).first() is not None
    id_expired = parsed.id_expiry < local_today()

    token = make_scan_token(
        {
            "id_number": parsed.id_number,
            "full_name": parsed.full_name,
            "dob": parsed.date_of_birth.isoformat(),
            "nationality": parsed.nationality,
            "gender": parsed.gender,
            "id_expiry": parsed.id_expiry.isoformat(),
        }
    )
    return ScanOut(
        scan_token=token, full_name=parsed.full_name, id_last4=parsed.id_number[-4:], nationality=parsed.nationality,
        gender=parsed.gender, date_of_birth=parsed.date_of_birth, id_expiry=parsed.id_expiry,
        id_expired=id_expired, already_checked_in=already,
    )


@router.post("/manual", response_model=ScanOut)
async def manual_id(
    body: ManualIdIn,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(current_user)],
):
    """Validates manually entered ID details and returns the same short-lived token as a scan."""
    today = local_today()
    if body.date_of_birth > today:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Date of birth cannot be in the future.")

    vault = get_vault()
    id_hash = vault.blind_index(body.id_number)
    already = (
        await db.execute(
            select(Visit.id).where(
                Visit.id_number_hash == id_hash,
                Visit.visit_date == today,
                Visit.checked_out_at.is_(None),
                Visit.deleted_at.is_(None),
            )
        )
    ).first() is not None
    token = make_scan_token(
        {
            "id_number": body.id_number,
            "full_name": body.full_name,
            "dob": body.date_of_birth.isoformat(),
            "nationality": body.nationality,
            "gender": body.gender,
            "id_expiry": body.id_expiry.isoformat(),
        }
    )
    return ScanOut(
        scan_token=token,
        full_name=body.full_name,
        id_last4=body.id_number[-4:],
        nationality=body.nationality,
        gender=body.gender,
        date_of_birth=body.date_of_birth,
        id_expiry=body.id_expiry,
        id_expired=body.id_expiry < today,
        already_checked_in=already,
    )


@router.post("", response_model=VisitOut, status_code=201)
async def create_visit(
    body: VisitCreateIn,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_csrf)],
):
    try:
        data = read_scan_token(body.scan_token)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This scan has expired. Please scan the ID again.")

    from datetime import date as _date, timedelta

    vault = get_vault()
    id_number = data["id_number"]
    id_hash = vault.blind_index(id_number)
    today = local_today()

    dup = (
        await db.execute(
            select(Visit.id).where(
                Visit.id_number_hash == id_hash, Visit.visit_date == today,
                Visit.checked_out_at.is_(None), Visit.deleted_at.is_(None),
            )
        )
    ).first()
    if dup:
        raise HTTPException(status.HTTP_409_CONFLICT, "This visitor is already checked in today.")

    visit = Visit(
        visit_date=today,
        full_name=data["full_name"][:120],
        id_number_hash=id_hash,
        id_last4=id_number[-4:],
        nationality=data["nationality"][:60],
        gender=data["gender"],
        id_expiry=_date.fromisoformat(data["id_expiry"]),
        id_expired=_date.fromisoformat(data["id_expiry"]) < today,
        floor=body.floor, purpose=body.purpose, host_name=body.host_name, department=body.department,
        phone=body.phone, company=body.company, vehicle_plate=body.vehicle_plate, notes=body.notes,
        created_by=user.id,
        id_number_enc="", dob_enc="",
    )
    db.add(visit)
    await db.flush()  # assigns visit.id (needed for AAD) and badge_no
    visit.id_number_enc = vault.encrypt(id_number, aad("id_number", visit.id))
    visit.dob_enc = vault.encrypt(data["dob"], aad("dob", visit.id))

    await write_audit(db, action="visit_created", user=user, target=visit.badge_no, detail=visit.full_name, ip=client_ip(request))
    await db.commit()
    return _to_out(visit)


@router.get("", response_model=VisitListOut)
async def list_visits(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(current_user)],
    q: str | None = Query(default=None, max_length=100),
    include_deleted: bool = Query(default=False),
    all_dates: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
):
    is_admin = user.role == "admin"
    stmt = select(Visit)
    if not is_admin or not all_dates:
        stmt = stmt.where(Visit.visit_date == local_today())
    if not is_admin or not include_deleted:
        stmt = stmt.where(Visit.deleted_at.is_(None))
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where((Visit.full_name.ilike(like)) | (Visit.company.ilike(like)) | (Visit.host_name.ilike(like)) | (Visit.badge_no.ilike(like)))

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    inside = (
        await db.execute(
            select(func.count()).select_from(
                stmt.where(Visit.checked_out_at.is_(None), Visit.deleted_at.is_(None)).subquery()
            )
        )
    ).scalar_one()
    rows = (
        await db.execute(stmt.order_by(Visit.checked_in_at.desc()).offset((page - 1) * page_size).limit(page_size))
    ).scalars().all()
    return VisitListOut(items=[_to_out(v) for v in rows], total=total, inside_count=inside)


@router.get("/stats", response_model=VisitStatsOut)
async def visit_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(current_user)],
):
    today = local_today()
    month_start = today.replace(day=1)
    next_month_start = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
    last_month_start = month_start - timedelta(days=1)
    last_month_start = last_month_start.replace(day=1)
    week_start = today - timedelta(days=today.weekday())
    active = Visit.deleted_at.is_(None)

    counts = (
        await db.execute(
            select(
                func.count(Visit.id).filter(active, Visit.visit_date == today).label("today_total"),
                func.count(Visit.id).filter(
                    active, Visit.visit_date == today, Visit.checked_out_at.is_(None)
                ).label("today_inside"),
                func.count(Visit.id).filter(
                    active, Visit.visit_date >= week_start, Visit.visit_date <= today
                ).label("this_week_total"),
                func.count(Visit.id).filter(
                    active, Visit.visit_date >= month_start, Visit.visit_date < next_month_start
                ).label("this_month_total"),
                func.count(Visit.id).filter(
                    active, Visit.visit_date >= last_month_start, Visit.visit_date < month_start
                ).label("last_month_total"),
            )
        )
    ).one()
    return VisitStatsOut(
        today_total=counts.today_total,
        today_inside=counts.today_inside,
        this_week_total=counts.this_week_total,
        this_month_total=counts.this_month_total,
        last_month_total=counts.last_month_total,
    )


@router.get("/departments", response_model=list[str])
async def list_departments(
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(current_user)],
):
    names = (await db.execute(select(Department.name).order_by(Department.name))).scalars().all()
    return list(names)


@router.get("/companies", response_model=list[str])
async def list_companies(
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[User, Depends(current_user)],
):
    names = (await db.execute(select(Company.name).order_by(Company.name))).scalars().all()
    return list(names)


@router.post("/{visit_id}/check-out", response_model=VisitOut)
async def check_out(
    visit_id: str,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_csrf)],
):
    visit = await db.get(Visit, visit_id)
    if visit is None or visit.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Visitor record not found")
    if visit.checked_out_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This visitor is already checked out")
    visit.checked_out_at = utcnow()
    await write_audit(db, action="visit_checked_out", user=user, target=visit.badge_no, detail=visit.full_name, ip=client_ip(request))
    await db.commit()
    return _to_out(visit)


@router.delete("/{visit_id}", status_code=204)
async def delete_visit(
    visit_id: str,
    body: DeleteVisitIn,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_role("admin"))],
):
    """Soft delete only: the row is hidden from normal views but kept, unaltered, for the audit trail."""
    visit = await db.get(Visit, visit_id)
    if visit is None or visit.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Visitor record not found")
    visit.deleted_at = utcnow()
    visit.deleted_by = user.username
    visit.delete_reason = body.reason
    await write_audit(db, action="visit_deleted", user=user, target=visit.badge_no, detail=body.reason, ip=client_ip(request))
    await db.commit()


@router.post("/{visit_id}/restore", response_model=VisitOut)
async def restore_visit(
    visit_id: str,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_role("admin"))],
):
    visit = await db.get(Visit, visit_id)
    if visit is None or visit.deleted_at is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No deleted record found")
    visit.deleted_at = None
    visit.deleted_by = None
    visit.delete_reason = None
    await write_audit(db, action="visit_restored", user=user, target=visit.badge_no, ip=client_ip(request))
    await db.commit()
    return _to_out(visit)
