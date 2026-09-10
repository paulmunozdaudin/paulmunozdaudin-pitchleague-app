import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.notification import NotificationOut
from app.services import notifications as notifications_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
def list_my_notifications(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[NotificationOut]:
    return notifications_service.list_my_notifications(db, user.id)


@router.post("/{notification_id}/read", status_code=204)
def mark_notification_read(
    notification_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> None:
    notifications_service.mark_read(db, user.id, notification_id)
