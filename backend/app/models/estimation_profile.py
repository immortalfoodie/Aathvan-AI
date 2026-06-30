"""Estimation profile model for tracking user-specific task estimates."""

from sqlalchemy import Column, Integer, Float, ForeignKey, Enum
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.models.task import TaskType

class UserEstimationProfile(Base):
    __tablename__ = "estimation_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    task_type = Column(Enum(TaskType), nullable=False)
    adjustment_factor = Column(Float, default=1.0, nullable=False)
    sample_count = Column(Integer, default=0, nullable=False)

    user = relationship("User", back_populates="estimation_profiles")
