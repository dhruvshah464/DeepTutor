"""
Auth Schemas
=============

Pydantic models for authentication request/response payloads.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field


# ── Requests ──

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: Optional[str] = Field(default=None, max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class MagicLinkRequest(BaseModel):
    email: EmailStr


class MagicLinkVerifyRequest(BaseModel):
    token: str


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class UpdateProfileRequest(BaseModel):
    display_name: Optional[str] = None
    bio: Optional[str] = None
    timezone: Optional[str] = None
    language: Optional[str] = None
    education_level: Optional[str] = None
    learning_goals: Optional[dict] = None
    subjects_of_interest: Optional[List[str]] = None


class UpdatePreferencesRequest(BaseModel):
    theme: Optional[str] = None
    font_size: Optional[str] = None
    compact_mode: Optional[bool] = None
    default_model: Optional[str] = None
    explanation_level: Optional[str] = None
    auto_suggestions: Optional[bool] = None
    email_notifications: Optional[bool] = None
    study_reminders: Optional[bool] = None
    weekly_digest: Optional[bool] = None


# ── Responses ──

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    id: str
    email: str
    email_verified: bool
    role: str
    is_active: bool
    auth_provider: str
    created_at: Optional[str] = None

    # Profile
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    timezone: Optional[str] = None
    language: Optional[str] = None
    education_level: Optional[str] = None
    learning_goals: Optional[dict] = None
    subjects_of_interest: Optional[List[str]] = None

    # Preferences
    theme: Optional[str] = None
    explanation_level: Optional[str] = None


class OrgResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: Optional[str] = None
    logo_url: Optional[str] = None
    role: str
    member_count: int = 0
    plan_tier: Optional[str] = None


class MeResponse(BaseModel):
    user: UserResponse
    orgs: List[OrgResponse] = []
    current_org: Optional[OrgResponse] = None
    plan_tier: str = "free"
