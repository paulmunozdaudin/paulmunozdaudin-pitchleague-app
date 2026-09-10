import uuid

from sqlalchemy.orm import Session

from app.db.base import utcnow
from app.models.notification import Notification


def create_notification(
    db: Session, user_id: uuid.UUID, type: str, title: str, body: str, league_id: uuid.UUID | None = None, data: dict | None = None
) -> Notification:
    notification = Notification(user_id=user_id, league_id=league_id, type=type, title=title, body=body, data=data)
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def list_my_notifications(db: Session, user_id: uuid.UUID, limit: int = 50) -> list[Notification]:
    return (
        db.query(Notification)
        .filter(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .all()
    )


def mark_read(db: Session, user_id: uuid.UUID, notification_id: uuid.UUID) -> None:
    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == user_id)
        .first()
    )
    if notification and notification.read_at is None:
        notification.read_at = utcnow()
        db.commit()
