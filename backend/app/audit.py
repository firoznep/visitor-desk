from sqlalchemy.ext.asyncio import AsyncSession

from .models import AuditLog, User


async def write_audit(
    db: AsyncSession,
    *,
    action: str,
    user: User | None = None,
    username: str | None = None,
    target: str | None = None,
    detail: str | None = None,
    ip: str | None = None,
) -> None:
    """Adds an audit row to the caller's transaction (action and log commit or fail together)."""
    db.add(
        AuditLog(
            user_id=user.id if user else None,
            username=user.username if user else username,
            action=action,
            target=target,
            detail=detail[:500] if detail else None,
            ip=ip,
        )
    )
