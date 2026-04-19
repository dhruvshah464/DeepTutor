"""
Admin API Router
=================

Global admin panel: user management, audit log, system health, feature flags.
"""

from __future__ import annotations

import logging
import os
import platform
import time

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from deeptutor.auth.dependencies import require_role
from deeptutor.database.engine import get_db_session
from deeptutor.database.models.audit import AuditLog
from deeptutor.database.models.billing import Plan, Subscription
from deeptutor.database.models.org import Organization
from deeptutor.database.models.session import ChatSession
from deeptutor.database.models.user import User

router = APIRouter()
logger = logging.getLogger(__name__)

_start_time = time.time()


@router.get("/admin/stats")
async def admin_stats(
    user=Depends(require_role("superadmin")),
    db: AsyncSession = Depends(get_db_session),
):
    """Get platform-wide statistics."""
    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    active_users = (
        await db.execute(select(func.count(User.id)).where(User.is_active == True))
    ).scalar() or 0
    total_orgs = (await db.execute(select(func.count(Organization.id)))).scalar() or 0
    total_sessions = (await db.execute(select(func.count(ChatSession.id)))).scalar() or 0
    active_subs = (
        await db.execute(
            select(func.count(Subscription.id)).where(Subscription.status == "active")
        )
    ).scalar() or 0

    # Plan distribution
    plan_dist = (
        await db.execute(
            select(Plan.tier, func.count(Subscription.id))
            .join(Subscription, Plan.id == Subscription.plan_id)
            .where(Subscription.status == "active")
            .group_by(Plan.tier)
        )
    ).all()

    return {
        "users": {"total": total_users, "active": active_users},
        "organizations": {"total": total_orgs},
        "sessions": {"total": total_sessions},
        "subscriptions": {"active": active_subs},
        "plan_distribution": {tier: count for tier, count in plan_dist},
        "uptime_seconds": time.time() - _start_time,
    }


@router.get("/admin/users")
async def admin_list_users(
    user=Depends(require_role("superadmin", "support")),
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    search: str = Query(default=""),
):
    """List all users with search and pagination."""
    query = select(User)
    if search:
        query = query.where(User.email.ilike(f"%{search}%"))
    query = query.order_by(User.created_at.desc()).limit(limit).offset(offset)

    users = (await db.execute(query)).scalars().all()
    total = (
        await db.execute(
            select(func.count(User.id)).where(User.email.ilike(f"%{search}%")) if search
            else select(func.count(User.id))
        )
    ).scalar() or 0

    return {
        "users": [
            {
                "id": u.id,
                "email": u.email,
                "role": u.role,
                "is_active": u.is_active,
                "auth_provider": u.auth_provider,
                "email_verified": u.email_verified,
                "created_at": str(u.created_at),
                "last_login_at": str(u.last_login_at) if u.last_login_at else None,
            }
            for u in users
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/admin/audit-log")
async def admin_audit_log(
    user=Depends(require_role("superadmin")),
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    action: str = Query(default=""),
    user_id: str = Query(default=""),
):
    """View the audit log."""
    query = select(AuditLog)
    if action:
        query = query.where(AuditLog.action == action)
    if user_id:
        query = query.where(AuditLog.user_id == user_id)
    query = query.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)

    logs = (await db.execute(query)).scalars().all()

    return {
        "logs": [
            {
                "id": log.id,
                "user_id": log.user_id,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "description": log.description,
                "ip_address": log.ip_address,
                "created_at": str(log.created_at),
            }
            for log in logs
        ],
        "limit": limit,
        "offset": offset,
    }


@router.get("/admin/health")
async def admin_health(
    user=Depends(require_role("superadmin")),
    db: AsyncSession = Depends(get_db_session),
):
    """System health dashboard with service status."""
    checks = {}

    # Database
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = {"status": "healthy", "type": "postgresql"}
    except Exception as e:
        checks["database"] = {"status": "unhealthy", "error": str(e)}

    # LLM
    try:
        from deeptutor.services.llm import get_llm_client
        llm = get_llm_client()
        checks["llm"] = {"status": "healthy", "model": llm.config.model}
    except Exception as e:
        checks["llm"] = {"status": "unhealthy", "error": str(e)}

    # Embedding
    try:
        from deeptutor.services.embedding import get_embedding_client
        embed = get_embedding_client()
        checks["embedding"] = {"status": "healthy"}
    except Exception as e:
        checks["embedding"] = {"status": "unavailable", "error": str(e)}

    # System info
    system_info = {
        "python_version": platform.python_version(),
        "os": platform.system(),
        "uptime_seconds": time.time() - _start_time,
        "pid": os.getpid(),
    }

    all_healthy = all(c.get("status") == "healthy" for c in checks.values())

    return {
        "status": "healthy" if all_healthy else "degraded",
        "checks": checks,
        "system": system_info,
    }


@router.post("/admin/users/{target_user_id}/deactivate")
async def deactivate_user(
    target_user_id: str,
    user=Depends(require_role("superadmin")),
    db: AsyncSession = Depends(get_db_session),
):
    """Deactivate a user account."""
    target = (await db.execute(select(User).where(User.id == target_user_id))).scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.role == "superadmin":
        raise HTTPException(status_code=400, detail="Cannot deactivate a superadmin")

    target.is_active = False
    await db.flush()

    # Log audit
    audit = AuditLog(
        user_id=user["sub"],
        action="admin.user.deactivate",
        resource_type="user",
        resource_id=target_user_id,
        description=f"Deactivated user {target.email}",
    )
    db.add(audit)

    return {"message": f"User {target.email} deactivated"}


@router.post("/admin/users/{target_user_id}/activate")
async def activate_user(
    target_user_id: str,
    user=Depends(require_role("superadmin")),
    db: AsyncSession = Depends(get_db_session),
):
    """Reactivate a user account."""
    target = (await db.execute(select(User).where(User.id == target_user_id))).scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    target.is_active = True
    await db.flush()

    return {"message": f"User {target.email} activated"}
