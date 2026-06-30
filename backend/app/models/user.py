"""User model."""

from sqlalchemy import Column, Integer, String, DateTime, Date
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=True)  # Nullable for Google-only users
    name = Column(String(255), nullable=False)
    
    # Google OAuth fields (In prod, these should be encrypted/stored in a proper vault)
    google_id = Column(String(255), unique=True, index=True, nullable=True)
    google_access_token = Column(String(2048), nullable=True)
    google_refresh_token = Column(String, nullable=True)
    
    current_streak_days = Column(Integer, default=0, nullable=False)
    last_active_date = Column(Date, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")
    estimation_profiles = relationship("UserEstimationProfile", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User id={self.id} email={self.email}>"
