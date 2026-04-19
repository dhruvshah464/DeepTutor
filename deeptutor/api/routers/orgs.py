"""
Organization API Router
========================

Organization CRUD, membership management, and invitation flows.
"""

from __future__ import annotations

import logging
import re
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from deeptutor.auth.dependencies import get_current_user
from deeptutor.auth.permissions import Permission, check_permission
from deeptutor.database.engine import get_db_session
from deeptutor.database.models.org import Invitation, OrgMembership, OrgRole, Organization

router = APIRouter()
logger = logging.getLogger(__name__)


# ── Schemas ──

class CreateOrgRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: str | None = None
    slug: str | None = Field(default=None, max_length=100, pattern=r"^[a-z0-9-]+$")


class UpdateOrgRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    logo_url: str | None = None


class InviteMemberRequest(BaseModel):
    email: EmailStr
    role: str = OrgRole.LEARNER.value


class UpdateMemberRoleRequest(BaseModel):
    role: str


# ── Endpoints ──

@router.post("/orgs", status_code=status.HTTP_201_CREATED)
async def create_org(
    body: CreateOrgRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Create a new organization. The creator becomes the owner."""
    user_id = user["sub"]
    slug = body.slug or re.sub(r"[^a-z0-9]+", "-", body.name.lower()).strip("-")

    # Check slug uniqueness
    existing = (await db.execute(select(Organization).where(Organization.slug == slug))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail=f"Organization slug '{slug}' already exists")

    org = Organization(
        name=body.name,
        slug=slug,
        description=body.description,
    )
    db.add(org)
    await db.flush()

    # Add creator as owner
    membership = OrgMembership(
        user_id=user_id,
        org_id=org.id,
        role=OrgRole.OWNER.value,
    )
    db.add(membership)
    await db.flush()

    logger.info("Organization created: %s by user %s", org.name, user_id)
    return {"id": org.id, "name": org.name, "slug": org.slug}


@router.get("/orgs")
async def list_orgs(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """List organizations the current user belongs to."""
    user_id = user["sub"]
    results = (
        await db.execute(
            select(Organization, OrgMembership.role)
            .join(OrgMembership, Organization.id == OrgMembership.org_id)
            .where(OrgMembership.user_id == user_id, OrgMembership.is_active == True)
        )
    ).all()

    return [
        {
            "id": org.id,
            "name": org.name,
            "slug": org.slug,
            "description": org.description,
            "logo_url": org.logo_url,
            "role": role,
            "created_at": str(org.created_at),
        }
        for org, role in results
    ]


@router.get("/orgs/{org_id}")
async def get_org(
    org_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get organization details."""
    org = (await db.execute(select(Organization).where(Organization.id == org_id))).scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Check membership
    member = (
        await db.execute(
            select(OrgMembership).where(
                OrgMembership.org_id == org_id,
                OrgMembership.user_id == user["sub"],
                OrgMembership.is_active == True,
            )
        )
    ).scalar_one_or_none()

    if not member and user.get("role") != "superadmin":
        raise HTTPException(status_code=403, detail="Not a member of this organization")

    # Get member count
    member_count = (
        await db.execute(
            select(func.count(OrgMembership.id)).where(
                OrgMembership.org_id == org_id, OrgMembership.is_active == True
            )
        )
    ).scalar() or 0

    return {
        "id": org.id,
        "name": org.name,
        "slug": org.slug,
        "description": org.description,
        "logo_url": org.logo_url,
        "is_active": org.is_active,
        "member_count": member_count,
        "settings": org.settings,
        "your_role": member.role if member else None,
        "created_at": str(org.created_at),
    }


@router.put("/orgs/{org_id}")
async def update_org(
    org_id: str,
    body: UpdateOrgRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Update organization details. Requires admin/owner role."""
    org = (await db.execute(select(Organization).where(Organization.id == org_id))).scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Check permission
    member = (
        await db.execute(
            select(OrgMembership).where(
                OrgMembership.org_id == org_id,
                OrgMembership.user_id == user["sub"],
                OrgMembership.role.in_([OrgRole.OWNER.value, OrgRole.ADMIN.value]),
            )
        )
    ).scalar_one_or_none()

    if not member and user.get("role") != "superadmin":
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    if body.name is not None:
        org.name = body.name
    if body.description is not None:
        org.description = body.description
    if body.logo_url is not None:
        org.logo_url = body.logo_url

    await db.flush()
    return {"message": "Organization updated"}


@router.get("/orgs/{org_id}/members")
async def list_members(
    org_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """List organization members."""
    from deeptutor.database.models.user import User, UserProfile

    results = (
        await db.execute(
            select(OrgMembership, User, UserProfile)
            .join(User, OrgMembership.user_id == User.id)
            .outerjoin(UserProfile, UserProfile.user_id == User.id)
            .where(OrgMembership.org_id == org_id, OrgMembership.is_active == True)
        )
    ).all()

    return [
        {
            "user_id": u.id,
            "email": u.email,
            "display_name": p.display_name if p else None,
            "avatar_url": p.avatar_url if p else None,
            "role": m.role,
            "joined_at": str(m.joined_at),
        }
        for m, u, p in results
    ]


@router.post("/orgs/{org_id}/members/invite")
async def invite_member(
    org_id: str,
    body: InviteMemberRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Invite a user to the organization."""
    # Check inviter has permission
    member = (
        await db.execute(
            select(OrgMembership).where(
                OrgMembership.org_id == org_id,
                OrgMembership.user_id == user["sub"],
                OrgMembership.role.in_([OrgRole.OWNER.value, OrgRole.ADMIN.value]),
            )
        )
    ).scalar_one_or_none()

    if not member and user.get("role") != "superadmin":
        raise HTTPException(status_code=403, detail="Insufficient permissions to invite")

    # Check if already a member
    existing_member = (
        await db.execute(
            select(OrgMembership)
            .join(User, OrgMembership.user_id == User.id)
            .where(User.email == body.email, OrgMembership.org_id == org_id)
        )
    ).scalar_one_or_none()
    if existing_member:
        raise HTTPException(status_code=409, detail="User is already a member")

    # Create invitation
    token = secrets.token_urlsafe(32)
    invitation = Invitation(
        org_id=org_id,
        email=body.email,
        role=body.role,
        invited_by=user["sub"],
        token=token,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(invitation)
    await db.flush()

    logger.info("Invitation sent to %s for org %s", body.email, org_id)
    return {"message": "Invitation sent", "token": token}


@router.delete("/orgs/{org_id}/members/{target_user_id}")
async def remove_member(
    org_id: str,
    target_user_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Remove a member from the organization."""
    member = (
        await db.execute(
            select(OrgMembership).where(
                OrgMembership.org_id == org_id,
                OrgMembership.user_id == target_user_id,
            )
        )
    ).scalar_one_or_none()

    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    if member.role == OrgRole.OWNER.value:
        raise HTTPException(status_code=400, detail="Cannot remove the owner")

    member.is_active = False
    await db.flush()

    return {"message": "Member removed"}


# Import for type annotation
from deeptutor.database.models.user import User  # noqa: E402
