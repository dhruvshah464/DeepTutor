"""
Auth API Router
================

Authentication endpoints: register, login, magic link, refresh, logout, me.
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from meridian.persistence.engine import get_db_session
from meridian.persistence.models.billing import Plan, Subscription
from meridian.persistence.models.org import Organization, OrgMembership
from meridian.persistence.models.user import User, UserPreferences, UserProfile
from meridian.platform.auth.dependencies import get_current_user
from meridian.platform.auth.jwt import (
    ACCESS_TOKEN_EXPIRE_SECONDS,
    create_access_token,
    create_magic_link_token,
    create_refresh_token,
    decode_magic_link_token,
    decode_token,
)
from meridian.platform.auth.passwords import hash_password, verify_password
from meridian.platform.auth.schemas import (
    LoginRequest,
    MagicLinkRequest,
    MagicLinkVerifyRequest,
    MeResponse,
    OrgResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Register a new user with email and password."""
    # Check if email already exists
    existing = (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    # Create user
    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        auth_provider="email",
    )
    db.add(user)
    await db.flush()

    # Create profile
    profile = UserProfile(
        user_id=user.id,
        display_name=body.display_name or body.email.split("@")[0],
    )
    db.add(profile)

    # Create preferences
    prefs = UserPreferences(user_id=user.id)
    db.add(prefs)

    # Create default free subscription
    free_plan = (await db.execute(select(Plan).where(Plan.tier == "free"))).scalar_one_or_none()
    if free_plan:
        sub = Subscription(
            user_id=user.id,
            plan_id=free_plan.id,
            status="active",
        )
        db.add(sub)

    await db.flush()

    logger.info("User registered: %s", user.email)

    # Generate tokens
    access = create_access_token(user.id, user.email, user.role)
    refresh = create_refresh_token(user.id)

    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=ACCESS_TOKEN_EXPIRE_SECONDS,
    )


@router.post("/auth/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Login with email and password."""
    user = (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none()
    if not user or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    # Update last login
    user.last_login_at = datetime.now(timezone.utc)
    await db.flush()

    # Get org context
    org_id = None
    org_role = None
    membership = (
        await db.execute(
            select(OrgMembership)
            .where(OrgMembership.user_id == user.id, OrgMembership.is_active.is_(True))
            .limit(1)
        )
    ).scalar_one_or_none()
    if membership:
        org_id = membership.org_id
        org_role = membership.role

    access = create_access_token(user.id, user.email, user.role, org_id=org_id, org_role=org_role)
    refresh = create_refresh_token(user.id)

    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=ACCESS_TOKEN_EXPIRE_SECONDS,
    )


@router.post("/auth/magic-link")
async def request_magic_link(
    body: MagicLinkRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Send a magic link to the user's email."""
    # Always return success to prevent email enumeration
    user = (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none()
    if user:
        token = create_magic_link_token(body.email)
        # In production, send email here
        logger.info("Magic link token generated for %s: %s", body.email, token[:20] + "...")
    return {"message": "If an account exists, a magic link has been sent to your email"}


@router.post("/auth/magic-link/verify", response_model=TokenResponse)
async def verify_magic_link(
    body: MagicLinkVerifyRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Verify a magic link token and return auth tokens."""
    try:
        email = decode_magic_link_token(body.token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired magic link",
        )

    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if not user:
        # Auto-register via magic link
        user = User(email=email, email_verified=True, auth_provider="magic_link")
        db.add(user)
        await db.flush()
        profile = UserProfile(user_id=user.id, display_name=email.split("@")[0])
        db.add(profile)
        prefs = UserPreferences(user_id=user.id)
        db.add(prefs)
        free_plan = (await db.execute(select(Plan).where(Plan.tier == "free"))).scalar_one_or_none()
        if free_plan:
            db.add(Subscription(user_id=user.id, plan_id=free_plan.id, status="active"))
        await db.flush()

    user.email_verified = True
    user.last_login_at = datetime.now(timezone.utc)
    await db.flush()

    access = create_access_token(user.id, user.email, user.role)
    refresh = create_refresh_token(user.id)

    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=ACCESS_TOKEN_EXPIRE_SECONDS,
    )


@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh_token(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Refresh an access token."""
    try:
        payload = decode_token(body.refresh_token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    user_id = payload.get("sub")
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or deactivated",
        )

    access = create_access_token(user.id, user.email, user.role)
    refresh = create_refresh_token(user.id)

    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=ACCESS_TOKEN_EXPIRE_SECONDS,
    )


@router.post("/auth/logout")
async def logout(user=Depends(get_current_user)):
    """Logout (client-side token invalidation)."""
    # JWT is stateless — client is responsible for discarding tokens
    # In production, add token to a blacklist with TTL
    return {"message": "Logged out successfully"}


@router.get("/auth/me", response_model=MeResponse)
async def get_me(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get the current user's full profile, orgs, and plan."""
    user_id = user.get("sub")
    if user_id == "anonymous":
        return MeResponse(
            user=UserResponse(
                id="anonymous",
                email="anonymous@local",
                email_verified=False,
                role="user",
                is_active=True,
                auth_provider="none",
            ),
            plan_tier="free",
        )

    db_user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get profile
    profile = (
        await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    ).scalar_one_or_none()

    # Get preferences
    prefs = (
        await db.execute(select(UserPreferences).where(UserPreferences.user_id == user_id))
    ).scalar_one_or_none()

    # Get orgs
    memberships = (
        await db.execute(
            select(OrgMembership, Organization)
            .join(Organization, OrgMembership.org_id == Organization.id)
            .where(OrgMembership.user_id == user_id, OrgMembership.is_active.is_(True))
        )
    ).all()

    orgs = [
        OrgResponse(
            id=org.id,
            name=org.name,
            slug=org.slug,
            description=org.description,
            logo_url=org.logo_url,
            role=mem.role,
        )
        for mem, org in memberships
    ]

    # Get plan tier
    sub = (
        await db.execute(
            select(Subscription, Plan)
            .join(Plan, Subscription.plan_id == Plan.id)
            .where(Subscription.user_id == user_id, Subscription.status == "active")
            .limit(1)
        )
    ).first()
    plan_tier = sub[1].tier if sub else "free"

    user_resp = UserResponse(
        id=db_user.id,
        email=db_user.email,
        email_verified=db_user.email_verified,
        role=db_user.role,
        is_active=db_user.is_active,
        auth_provider=db_user.auth_provider,
        created_at=str(db_user.created_at) if db_user.created_at else None,
        display_name=profile.display_name if profile else None,
        avatar_url=profile.avatar_url if profile else None,
        bio=profile.bio if profile else None,
        timezone=profile.timezone if profile else None,
        language=profile.language if profile else None,
        education_level=profile.education_level if profile else None,
        learning_goals=profile.learning_goals if profile else None,
        subjects_of_interest=profile.subjects_of_interest if profile else None,
        theme=prefs.theme if prefs else None,
        explanation_level=prefs.explanation_level if prefs else None,
    )

    current_org = orgs[0] if orgs else None

    return MeResponse(
        user=user_resp,
        orgs=orgs,
        current_org=current_org,
        plan_tier=plan_tier,
    )
