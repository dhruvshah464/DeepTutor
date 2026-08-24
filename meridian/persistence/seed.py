"""
Seed Data
=========

Default data for plans, roles, and demo content.
Run with: python -m meridian.persistence.seed
"""

from __future__ import annotations

import asyncio
import logging

from meridian.persistence.engine import get_async_session, init_db
from meridian.persistence.models.billing import Plan, PlanTier

logger = logging.getLogger(__name__)

DEFAULT_PLANS = [
    {
        "name": "Free",
        "tier": PlanTier.FREE.value,
        "description": "Get started with AI-powered learning",
        "price_monthly": 0.0,
        "price_yearly": 0.0,
        "max_sessions_per_day": 5,
        "max_messages_per_day": 30,
        "max_tokens_per_month": 50_000,
        "max_knowledge_bases": 1,
        "max_uploads_per_month": 3,
        "max_upload_size_mb": 5,
        "max_searches_per_day": 10,
        "max_org_seats": None,
        "features": {
            "chat": True,
            "deep_solve": False,
            "deep_question": True,
            "deep_research": False,
            "knowledge_base": True,
            "flashcards": True,
            "quizzes": True,
            "learning_paths": False,
            "analytics": False,
            "export_pdf": False,
            "priority_support": False,
            "custom_tutorbot": False,
        },
    },
    {
        "name": "Pro",
        "tier": PlanTier.PRO.value,
        "description": "Unlock the full power of AI tutoring",
        "price_monthly": 19.0,
        "price_yearly": 190.0,
        "max_sessions_per_day": 50,
        "max_messages_per_day": 500,
        "max_tokens_per_month": 1_000_000,
        "max_knowledge_bases": 10,
        "max_uploads_per_month": 50,
        "max_upload_size_mb": 50,
        "max_searches_per_day": 100,
        "max_org_seats": None,
        "features": {
            "chat": True,
            "deep_solve": True,
            "deep_question": True,
            "deep_research": True,
            "knowledge_base": True,
            "flashcards": True,
            "quizzes": True,
            "learning_paths": True,
            "analytics": True,
            "export_pdf": True,
            "priority_support": False,
            "custom_tutorbot": True,
            "adaptive_difficulty": True,
            "skill_graph": True,
            "exam_simulator": True,
        },
    },
    {
        "name": "Team",
        "tier": PlanTier.TEAM.value,
        "description": "Collaborate and learn together",
        "price_monthly": 49.0,
        "price_yearly": 490.0,
        "max_sessions_per_day": 200,
        "max_messages_per_day": 2000,
        "max_tokens_per_month": 5_000_000,
        "max_knowledge_bases": 50,
        "max_uploads_per_month": 200,
        "max_upload_size_mb": 100,
        "max_searches_per_day": 500,
        "max_org_seats": 10,
        "features": {
            "chat": True,
            "deep_solve": True,
            "deep_question": True,
            "deep_research": True,
            "knowledge_base": True,
            "flashcards": True,
            "quizzes": True,
            "learning_paths": True,
            "analytics": True,
            "export_pdf": True,
            "priority_support": True,
            "custom_tutorbot": True,
            "adaptive_difficulty": True,
            "skill_graph": True,
            "exam_simulator": True,
            "team_analytics": True,
            "shared_knowledge_bases": True,
        },
    },
    {
        "name": "School",
        "tier": PlanTier.SCHOOL.value,
        "description": "For classrooms and educational institutions",
        "price_monthly": 199.0,
        "price_yearly": 1990.0,
        "max_sessions_per_day": 1000,
        "max_messages_per_day": 10000,
        "max_tokens_per_month": 20_000_000,
        "max_knowledge_bases": 200,
        "max_uploads_per_month": 1000,
        "max_upload_size_mb": 200,
        "max_searches_per_day": 2000,
        "max_org_seats": 100,
        "features": {
            "chat": True,
            "deep_solve": True,
            "deep_question": True,
            "deep_research": True,
            "knowledge_base": True,
            "flashcards": True,
            "quizzes": True,
            "learning_paths": True,
            "analytics": True,
            "export_pdf": True,
            "priority_support": True,
            "custom_tutorbot": True,
            "adaptive_difficulty": True,
            "skill_graph": True,
            "exam_simulator": True,
            "team_analytics": True,
            "shared_knowledge_bases": True,
            "classroom_mode": True,
            "educator_dashboard": True,
            "student_progress_reports": True,
            "lms_integration": True,
        },
    },
    {
        "name": "Enterprise",
        "tier": PlanTier.ENTERPRISE.value,
        "description": "Custom solutions for large organizations",
        "price_monthly": 0.0,  # Custom pricing
        "price_yearly": 0.0,
        "max_sessions_per_day": 999999,
        "max_messages_per_day": 999999,
        "max_tokens_per_month": 999_999_999,
        "max_knowledge_bases": 999999,
        "max_uploads_per_month": 999999,
        "max_upload_size_mb": 500,
        "max_searches_per_day": 999999,
        "max_org_seats": None,
        "features": {
            "chat": True,
            "deep_solve": True,
            "deep_question": True,
            "deep_research": True,
            "knowledge_base": True,
            "flashcards": True,
            "quizzes": True,
            "learning_paths": True,
            "analytics": True,
            "export_pdf": True,
            "priority_support": True,
            "custom_tutorbot": True,
            "adaptive_difficulty": True,
            "skill_graph": True,
            "exam_simulator": True,
            "team_analytics": True,
            "shared_knowledge_bases": True,
            "classroom_mode": True,
            "educator_dashboard": True,
            "student_progress_reports": True,
            "lms_integration": True,
            "sso": True,
            "audit_log": True,
            "custom_branding": True,
            "api_access": True,
            "dedicated_support": True,
            "sla": True,
        },
    },
]


async def seed_plans() -> None:
    """Insert default plans if they don't exist."""
    from sqlalchemy import select

    async with get_async_session() as session:
        existing = (await session.execute(select(Plan.name))).scalars().all()
        for plan_data in DEFAULT_PLANS:
            if plan_data["name"] not in existing:
                plan = Plan(**plan_data)
                session.add(plan)
                logger.info("Seeded plan: %s", plan_data["name"])


async def seed_all() -> None:
    """Run all seed operations."""
    await init_db()
    await seed_plans()
    logger.info("Database seeding complete")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(seed_all())
