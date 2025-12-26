from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user
from models import UserStat
from schemas.user_stats import UserStatsResponse

router = APIRouter(prefix="/user", tags=["User"])

@router.get("/stats", response_model=UserStatsResponse)
def get_user_stats(
    user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stats = (
        db.query(UserStat)
        .filter(UserStat.user_id == user.id)
        .first()
    )

    if not stats:
        raise HTTPException(status_code=404, detail="User stats not found")

    return stats
