"""TaskStep model — individual steps within a task."""

import enum

from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.base import Base


class StepStatus(str, enum.Enum):
    """Progress status for an individual step."""
    pending = "pending"
    in_progress = "in_progress"
    done = "done"
    skipped = "skipped"


class TaskStep(Base):
    __tablename__ = "task_steps"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(
        Integer,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    estimated_hours = Column(Float, nullable=True)  # AI fills this in Step 2
    order_index = Column(Integer, nullable=False, default=0)
    scheduled_date = Column(DateTime(timezone=True), nullable=True)  # Scheduling in Step 2+
    status = Column(SQLEnum(StepStatus), default=StepStatus.pending, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)  # Auto-set when status → done
    # Data capture only in Step 3 — estimation-learning logic will use this in a future step
    actual_hours_spent = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    task = relationship("Task", back_populates="steps")

    def __repr__(self):
        return f"<TaskStep id={self.id} title={self.title!r}>"
