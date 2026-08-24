"""
ORM Models
==========

All SQLAlchemy models for the DeepTutor SaaS platform.
"""

from .audit import AuditLog
from .base import Base, TenantMixin, TimestampMixin
from .billing import Invoice, Plan, Subscription, UsageRecord
from .knowledge import Chunk, Document, KnowledgeBaseModel
from .learning import Flashcard, FlashcardDeck, LearningPath, LearningProgress, Quiz, QuizAttempt
from .org import Invitation, Organization, OrgMembership
from .session import ChatMessage, ChatSession
from .user import User, UserPreferences, UserProfile

__all__ = [
    "Base",
    "TenantMixin",
    "TimestampMixin",
    # User
    "User",
    "UserProfile",
    "UserPreferences",
    # Organization
    "Organization",
    "OrgMembership",
    "Invitation",
    # Session
    "ChatSession",
    "ChatMessage",
    # Knowledge
    "KnowledgeBaseModel",
    "Document",
    "Chunk",
    # Billing
    "Plan",
    "Subscription",
    "UsageRecord",
    "Invoice",
    # Audit
    "AuditLog",
    # Learning
    "LearningPath",
    "LearningProgress",
    "Quiz",
    "QuizAttempt",
    "FlashcardDeck",
    "Flashcard",
]
