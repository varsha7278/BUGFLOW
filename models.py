import enum
from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Enum,
    ForeignKey,
    Boolean
)

from database import Base


# ==========================================================
# ENUMS
# ==========================================================

class IssueType(enum.Enum):
    BUG = "BUG"
    FEATURE_REQUEST = "FEATURE_REQUEST"
    ENHANCEMENT = "ENHANCEMENT"
    TECHNICAL_DEBT = "TECHNICAL_DEBT"
    SUPPORT_TICKET = "SUPPORT_TICKET"


class Severity(enum.Enum):
    MINOR = "MINOR"
    MAJOR = "MAJOR"
    CRITICAL = "CRITICAL"
    BLOCKER = "BLOCKER"


class Priority(enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class IssueStatus(enum.Enum):
    REPORTED = "REPORTED"
    TRIAGED = "TRIAGED"
    IN_PROGRESS = "IN_PROGRESS"
    IN_REVIEW = "IN_REVIEW"
    TESTING = "TESTING"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class SprintStatus(enum.Enum):
    PLANNING = "PLANNING"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"


# ==========================================================
# USER TABLE
# ==========================================================

class User(Base):
    __tablename__ = "users"

    id = Column(
        Integer,
        primary_key=True
    )

    name = Column(
        String(150),
        nullable=False
    )

    email = Column(
        String(150),
        unique=True,
        nullable=False
    )

    password_hash = Column(
        String(255),
        nullable=False
    )

    role = Column(
        String(20),
        default="user",
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )


# ==========================================================
# SPRINT TABLE
# ==========================================================

class Sprint(Base):
    __tablename__ = "sprints"

    id = Column(
        Integer,
        primary_key=True
    )

    name = Column(
        String(200),
        nullable=False
    )

    goal = Column(
        Text,
        nullable=True
    )

    status = Column(
        Enum(SprintStatus),
        default=SprintStatus.PLANNING,
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )


# ==========================================================
# ISSUE TABLE
# ==========================================================

class Issue(Base):
    __tablename__ = "issues"

    id = Column(
        Integer,
        primary_key=True
    )

    issue_key = Column(
        String(50),
        unique=True,
        nullable=False
    )

    issue_type = Column(
        Enum(IssueType),
        nullable=False
    )

    title = Column(
        String(200),
        nullable=False
    )

    description = Column(
        Text,
        nullable=False
    )

    reproduction_steps = Column(
        Text,
        nullable=True
    )

    status = Column(
        Enum(IssueStatus),
        default=IssueStatus.REPORTED,
        nullable=False
    )

    severity = Column(
        Enum(Severity),
        nullable=False
    )

    priority = Column(
        Enum(Priority),
        nullable=False
    )

    affected_module = Column(
        String(200),
        nullable=True
    )

    environment = Column(
        String(200),
        nullable=True
    )

    project_key = Column(
        String(50),
        nullable=False
    )

    reporter_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    assignee_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )

    sprint_id = Column(
        Integer,
        ForeignKey("sprints.id"),
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # ======================================================
    # MILESTONE 3 FIELDS
    # ======================================================

    resolved_at = Column(
        DateTime,
        nullable=True
    )

    production_bug = Column(
        Boolean,
        default=False,
        nullable=False
    )


# ==========================================================
# AUDIT LOG TABLE
# ==========================================================

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(
        Integer,
        primary_key=True
    )

    issue_id = Column(
        Integer,
        ForeignKey("issues.id"),
        nullable=False
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )

    action = Column(
        String(100),
        nullable=False
    )

    details = Column(
        Text,
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )