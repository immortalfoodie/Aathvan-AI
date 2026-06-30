"""Router for user notifications."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.notification import Notification
from app.schemas.notification import NotificationResponse
from app.services.notifier import generate_notification_for_user

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=List[NotificationResponse])
def get_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve the most recent notifications for the current user."""
    notifications = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(20)
        .all()
    )
    return notifications


@router.patch("/{notification_id}", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark a notification as read."""
    notification = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
        .first()
    )
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    notification.read = True
    db.commit()
    db.refresh(notification)
    return notification


@router.post("/generate-now", response_model=NotificationResponse)
def trigger_notification_now(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Immediately trigger daily notification generation for the current user (for demo purposes)."""
    notif = generate_notification_for_user(current_user, db)
    if not notif:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No priorities found. Cannot generate notification.",
        )
    return notif
