from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user
from models import UserStat
from schemas.user_stats import UserStatsResponse, DifficultyUpdateRequest

from kite import kite_connect
from security import decrypt_token
from scheduler import check_dsa_completion

router = APIRouter(prefix="/user", tags=["User"])

@router.post("/sync", response_model=UserStatsResponse)
def sync_user_progress(
    user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    check_dsa_completion(db)
    stats = db.query(UserStat).filter(UserStat.user_id == user.id).first()
    if not stats:
        raise HTTPException(status_code=404, detail="User stats not found")
    
    # Format name according to existing logic
    if user.name:
        parts = user.name.split()
        if len(parts) > 2:
            stats.name = f"{parts[0]} {parts[-1]}"
        else:
            stats.name = user.name
    else:
        stats.name = "User"
    stats.email = user.email

    return stats

@router.post("/difficulty", response_model=UserStatsResponse)
def update_difficulty(
    request: DifficultyUpdateRequest,
    user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stats = db.query(UserStat).filter(UserStat.user_id == user.id).first()
    if not stats:
        raise HTTPException(status_code=404, detail="User stats not found")
    
    new_mode = request.difficulty_mode.lower()
    if new_mode not in ["sandbox", "normal", "hardcore", "god"]:
        raise HTTPException(status_code=400, detail="Invalid difficulty mode")
    
    stats.difficulty_mode = new_mode
    
    # Reset/Cap lives based on mode
    if new_mode == "hardcore":
        stats.lives = min(stats.lives, 1)
    elif new_mode == "normal":
        stats.lives = min(stats.lives, 5)
    elif new_mode == "sandbox" or new_mode == "god":
        stats.lives = 0 # Lives don't matter in sandbox, no buffer in god mode
    
    db.commit()
    return stats

@router.post("/use-powerup", response_model=UserStatsResponse)
def use_powerup(
    user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stats = db.query(UserStat).filter(UserStat.user_id == user.id).first()
    if not stats:
        raise HTTPException(status_code=404, detail="User stats not found")
    
    mode = stats.difficulty_mode.lower()
    
    if mode == "god":
        raise HTTPException(status_code=403, detail="God mode allows ZERO powerups. Absolute accountability.")

    if mode == "hardcore":
        if stats.powerups_used_today >= 1:
            raise HTTPException(status_code=403, detail="Hardcore mode allows only 1 powerup per day")
    
    # Logic for using the powerup (e.g., skip today)
    # For now, let's just increment the counter
    stats.powerups_used_today += 1
    db.commit()
    return stats

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

    if user.name:
        parts = user.name.split()
        if len(parts) > 2:
            stats.name = f"{parts[0]} {parts[-1]}"
        else:
            stats.name = user.name
    else:
        stats.name = "User"
    
    stats.email = user.email

    return stats

@router.get("/margins")
def get_user_margins(
    user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not user.access_token:
        raise HTTPException(status_code=400, detail="Zerodha account not linked")
    
    try:
        access_token = decrypt_token(user.access_token)
        kite_connect.set_access_token(access_token)
        margins = kite_connect.margins()
        
        # Sync with database stats
        equity_margin = margins.get("equity", {}).get("available", {}).get("live_balance", 0)
        from models import UserStat
        stats = db.query(UserStat).filter(UserStat.user_id == user.id).first()
        if stats:
            stats.available_balance = equity_margin
            db.commit()
            
        return margins
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch margins: {str(e)}")
