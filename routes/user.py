from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict

from ..database import get_db  # Adjust import as needed
from ..models import User  # Adjust import as needed

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/{user_id}/stats", response_model=Dict[str, int])
def get_user_stats(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Example stats, adjust according to your User model
    stats = {
        "games_played": user.games_played,
        "games_won": user.games_won,
        "score": user.score
    }
    return stats