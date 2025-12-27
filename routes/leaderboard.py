from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import User, UserStat
from schemas.leaderboard import LeaderboardResponse, LeaderboardEntry
from typing import List

router = APIRouter(prefix="/leaderboard", tags=["Leaderboard"])

@router.get("/", response_model=LeaderboardResponse)
def get_leaderboard(db: Session = Depends(get_db)):
    # Join UserStat with User to get names and public_id
    # Sort by total_xp descending
    results = (
        db.query(UserStat, User)
        .join(User, UserStat.user_id == User.id)
        .order_by(UserStat.total_xp.desc())
        .limit(100)
        .all()
    )
    
    entries = []
    for i, (stat, user) in enumerate(results):
        # Format name logic (consistent with user.py)
        name = "User"
        if user.name:
            parts = user.name.split()
            name = f"{parts[0]} {parts[-1]}" if len(parts) > 2 else user.name
            
        entries.append(LeaderboardEntry(
            rank=i + 1,
            name=name,
            total_xp=stat.total_xp,
            problems_solved=stat.problems_solved,
            current_streak=stat.current_streak,
            public_id=user.public_id
        ))
        
    return LeaderboardResponse(entries=entries)
