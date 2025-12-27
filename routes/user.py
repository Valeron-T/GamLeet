from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user
from models import UserStat
from schemas.user_stats import UserStatsResponse, DifficultyUpdateRequest

from kite import kite_connect
from security import decrypt_token
from scheduler import check_dsa_completion
from dependencies import get_redis_client 
import json

router = APIRouter(prefix="/user", tags=["User"])

async def fetch_and_cache_margins(user, redis):
    cache_key = f"user:{user.id}:margins"
    
    # Check cache
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # Fetch from Zerodha if access token exists
    if not user.access_token:
        return {"equity": {"available": {"live_balance": 0}}}
        
    try:
        from kite import kite_connect
        access_token = decrypt_token(user.access_token)
        kite_connect.set_access_token(access_token)
        margins = kite_connect.margins()
        
        # Cache for 1 hour
        await redis.set(cache_key, json.dumps(margins), ex=3600)
        return margins
    except Exception as e:
        print(f"Error fetching margins: {e}")
        return {"equity": {"available": {"live_balance": 0}}}

@router.post("/sync", response_model=UserStatsResponse)
async def sync_user_progress(
    user = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis = Depends(get_redis_client),
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

    # Inject real-time balance
    margins = await fetch_and_cache_margins(user, redis)
    stats.available_balance = margins.get("equity", {}).get("available", {}).get("live_balance", 0)

    return stats

@router.post("/disconnect-zerodha")
async def disconnect_zerodha(
    user = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis = Depends(get_redis_client),
):
    user.access_token = None
    user.zerodha_id = None
    
    # Clear cache
    await redis.delete(f"user:{user.id}:margins")
    
    stats = db.query(UserStat).filter(UserStat.user_id == user.id).first()
    if stats:
        stats.lives = 3 
        stats.difficulty_mode = "normal"
    
    db.commit()
    return {"message": "Zerodha account disconnected successfully"}

@router.post("/difficulty", response_model=UserStatsResponse)
async def update_difficulty(
    request: DifficultyUpdateRequest,
    user = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis = Depends(get_redis_client),
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

    # Populate response fields
    if user.name:
        parts = user.name.split()
        stats.name = f"{parts[0]} {parts[-1]}" if len(parts) > 2 else user.name
    else:
        stats.name = "User"
    stats.email = user.email
    
    margins = await fetch_and_cache_margins(user, redis)
    stats.available_balance = margins.get("equity", {}).get("available", {}).get("live_balance", 0)

    return stats

@router.post("/use-powerup", response_model=UserStatsResponse)
async def use_powerup(
    user = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis = Depends(get_redis_client),
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

    # Populate response fields
    if user.name:
        parts = user.name.split()
        stats.name = f"{parts[0]} {parts[-1]}" if len(parts) > 2 else user.name
    else:
        stats.name = "User"
    stats.email = user.email
    
    margins = await fetch_and_cache_margins(user, redis)
    stats.available_balance = margins.get("equity", {}).get("available", {}).get("live_balance", 0)

    return stats

@router.get("/stats", response_model=UserStatsResponse)
async def get_user_stats(
    user = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis = Depends(get_redis_client),
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

    # Inject real-time balance from Redis/Zerodha
    if user.access_token:
        margins = await fetch_and_cache_margins(user, redis)
        stats.available_balance = margins.get("equity", {}).get("available", {}).get("live_balance", 0)
    else:
        stats.available_balance = 0

    return stats

@router.get("/margins")
async def get_user_margins(
    user = Depends(get_current_user),
    redis = Depends(get_redis_client),
):
    if not user.access_token:
        # Return properly structured empty response for UI to handle gracefully
        return {"equity": {"available": {"live_balance": 0}}}
    
    return await fetch_and_cache_margins(user, redis)
