"""Task model with type and status enums."""

import enum

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.base import Base


class TaskType(str, enum.Enum):
    """Types of tasks the system can manage."""
    assignment = "assignment"
    project = "project"
    bill = "bill"
    application = "application"
    personal_goal = "personal_goal"
    other = "other"


class TaskStatus(str, enum.Enum):
    """High-level task progress status."""
    not_started = "not_started"
    in_progress = "in_progress"
    completed = "completed"


class AIPlanStatus(str, enum.Enum):
    """AI decomposition plan status."""
    not_generated = "not_generated"
    pending_approval = "pending_approval"
    approved = "approved"


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    raw_description = Column(Text, nullable=True)  # Will hold pasted assignment/syllabus text for AI
    task_type = Column(SQLEnum(TaskType), default=TaskType.other, nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.not_started, nullable=False)
    ai_plan_status = Column(SQLEnum(AIPlanStatus), default=AIPlanStatus.not_generated, nullable=False)
    task_summary = Column(Text, nullable=True)
    ai_confidence_note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    user = relationship("User", back_populates="tasks")
    steps = relationship(
        "TaskStep",
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="TaskStep.order_index",
    )

    def __repr__(self):
        return f"<Task id={self.id} title={self.title!r}>"
