from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.entities import Notification, User
from app.schemas.api_schemas import NotificationOut
from app.api.deps import get_current_user

router = APIRouter()

@router.get("/", response_model=List[NotificationOut])
def list_notifications(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return notifications strictly belonging to the currently authenticated user."""
    notifs = db.query(Notification).filter(
        Notification.user_id == user.id
    ).order_by(Notification.created_at.desc()).limit(30).all()
    return notifs

@router.patch("/{id}/read")
def mark_read(
    id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark a notification as read with strict user ownership validation."""
    notif = db.query(Notification).filter(
        Notification.id == id,
        Notification.user_id == user.id
    ).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.is_read = True
    db.commit()
    return {"status": "success"}
