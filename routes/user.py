from fastapi import APIRouter, Depends, HTTPException, Header, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_redis_client, get_current_user
from models import UserStat, UserInventory, UserAchievement, Question
from schemas.user_stats import UserStatsResponse, DifficultyUpdateRequest
from schemas.inventory import InventoryResponse, InventoryItem, AchievementsResponse, Achievement, PowerupPurchaseRequest
from schemas.user_leetcode import LeetCodeUpdate

from security import decrypt_token, encrypt_token
from scheduler import check_all_users_dsa
from schemas.zerodha import ZerodhaCredentialsUpdate
from schemas.zerodha import ZerodhaCredentialsUpdate
import json

router = APIRouter(prefix="/user", tags=["User"])

async def fetch_and_cache_margins(user, redis):
    cache_key = f"user:{user.id}:margins"
    
    # Check cache
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # Fetch from Zerodha if access token exists
    if not user.access_token or not user.zerodha_api_key:
        return {"equity": {"available": {"live_balance": 0}}, "error": "No credentials"}
        
    try:
        from kite import get_kite_client
        api_key = decrypt_token(user.zerodha_api_key)
        access_token = decrypt_token(user.access_token)
        
        kite_client = get_kite_client(api_key)
        kite_client.set_access_token(access_token)
        margins = kite_client.margins()
        
        # Cache for 1 hour
        await redis.set(cache_key, json.dumps(margins), ex=3600)
        return margins
    except Exception as e:
        print(f"Error fetching margins for user {user.id}: {e}")
        return {"equity": {"available": {"live_balance": 0}}, "error": str(e)}

def extract_wallet_balance(margins):
    """Safely extracts the most relevant balance from Zerodha margins response."""
    if not margins:
        return 0
    
    def get_seg_balance(seg_data):
        if not seg_data:
            return 0
        available = seg_data.get("available", {})
        # Priority: Net > Live Balance > Cash > Opening
        return (seg_data.get("net") or 
                available.get("live_balance") or 
                available.get("cash") or 
                available.get("opening_balance") or 0)

    equity_balance = get_seg_balance(margins.get("equity", {}))
    commodity_balance = get_seg_balance(margins.get("commodity", {}))
    
    # Return total balance across both segments
    return (equity_balance or 0) + (commodity_balance or 0)

@router.post("/sync", response_model=UserStatsResponse)
async def sync_user_progress(
    user = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis = Depends(get_redis_client),
):
    from scheduler import check_dsa_completion
    check_dsa_completion(user, db)
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
    stats.available_balance = extract_wallet_balance(margins)
    stats.zerodha_error = margins.get("error")
    stats.leetcode_connected = bool(user.leetcode_session)
    stats.leetcode_username = user.leetcode_username
    stats.zerodha_connected = bool(user.zerodha_api_key)
    stats.allow_paid = user.allow_paid
    stats.risk_locked = bool(stats.risk_locked)

    return stats


@router.get("/login")
def start_zerodha_login(
    user = Depends(get_current_user),
    db: Session = Depends(get_db)
): 
    """
    Initiates the Zerodha login flow for the current authenticated user.
    """
    if not user.zerodha_api_key:
        raise HTTPException(status_code=400, detail="Zerodha API credentials not configured")
        
    try:
        from kite import get_kite_client
        api_key = decrypt_token(user.zerodha_api_key)
        kite_client = get_kite_client(api_key)
        
        # In a multi-tenant app, we'd ideally pass the public_id as 'state' 
        # to identify the user on callback.
        login_url = kite_client.login_url()
        
        return RedirectResponse(url=login_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate login URL: {str(e)}")


@router.post("/disconnect-zerodha")
async def disconnect_zerodha(
    user = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis = Depends(get_redis_client),
):
    user.access_token = None
    user.zerodha_api_key = None
    user.zerodha_api_secret = None
    
    # Clear cache
    await redis.delete(f"user:{user.id}:margins")
    
    stats = db.query(UserStat).filter(UserStat.user_id == user.id).first()
    if stats:
        stats.lives = 3 
        stats.difficulty_mode = "normal"
    
    db.commit()
    return {"message": "Zerodha account disconnected successfully"}

@router.post("/leetcode")
async def update_leetcode_credentials(
    request: LeetCodeUpdate,
    user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user.leetcode_username = request.username
    user.leetcode_session = request.session
    user.allow_paid = request.allow_paid
    db.commit()
    return {"message": "LeetCode credentials updated successfully"}

@router.post("/zerodha")
async def update_zerodha_credentials(
    request: ZerodhaCredentialsUpdate,
    user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user.zerodha_api_key = encrypt_token(request.api_key.strip())
    user.zerodha_api_secret = encrypt_token(request.api_secret.strip())
    db.commit()
    return {"message": "Zerodha credentials updated successfully"}

@router.post("/difficulty", response_model=UserStatsResponse)
async def update_difficulty(
    request: DifficultyUpdateRequest,
    user = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis = Depends(get_redis_client),
):
    stats = db.query(UserStat).filter(UserStat.user_id == user.id).first()
    if not stats:
        # Self-healing: Create stats if missing
        stats = UserStat(user_id=user.id)
        db.add(stats)
        db.commit()
        db.refresh(stats)
    
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
    
    if request.daily_risk_amount is not None:
        stats.daily_risk_amount = request.daily_risk_amount
        
    if request.risk_locked is not None:
        stats.risk_locked = 1 if request.risk_locked else 0
    
    db.commit()

    # Populate response fields
    if user.name:
        parts = user.name.split()
        stats.name = f"{parts[0]} {parts[-1]}" if len(parts) > 2 else user.name
    else:
        stats.name = "User"
    stats.email = user.email
    
    margins = await fetch_and_cache_margins(user, redis)
    stats.available_balance = extract_wallet_balance(margins)
    stats.zerodha_error = margins.get("error")
    stats.leetcode_connected = bool(user.leetcode_session)
    stats.leetcode_username = user.leetcode_username
    stats.zerodha_connected = bool(user.zerodha_api_key)
    stats.allow_paid = user.allow_paid
    stats.risk_locked = bool(stats.risk_locked) # Convert integer to bool for response

    return stats

@router.post("/use-powerup", response_model=UserStatsResponse)
async def use_powerup(
    user = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis = Depends(get_redis_client),
):
    stats = db.query(UserStat).filter(UserStat.user_id == user.id).first()
    if not stats:
        # Self-healing: Create stats if missing
        stats = UserStat(user_id=user.id)
        db.add(stats)
        db.commit()
        db.refresh(stats)
    
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
    stats.available_balance = extract_wallet_balance(margins)
    stats.zerodha_error = margins.get("error")
    stats.leetcode_connected = bool(user.leetcode_session)
    stats.leetcode_username = user.leetcode_username
    stats.zerodha_connected = bool(user.zerodha_api_key)
    stats.allow_paid = user.allow_paid
    stats.risk_locked = bool(stats.risk_locked)

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
        # Self-healing: Create stats if missing
        stats = UserStat(user_id=user.id)
        db.add(stats)
        
        # Also initialize inventory
        inventory_exists = db.query(UserInventory).filter(UserInventory.user_id == user.id).first()
        if not inventory_exists:
            starter_items = [
                UserInventory(user_id=user.id, item_id="streak-freeze", quantity=1),
                UserInventory(user_id=user.id, item_id="penalty-shield", quantity=1)
            ]
            for item in starter_items:
                db.add(item)
                
        db.commit()
        db.refresh(stats)
    
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
        stats.available_balance = extract_wallet_balance(margins)
        stats.zerodha_error = margins.get("error")
    else:
        stats.available_balance = 0
        stats.zerodha_error = "Zerodha not connected"
    
    stats.leetcode_connected = bool(user.leetcode_session)
    stats.leetcode_username = user.leetcode_username
    stats.zerodha_connected = bool(user.zerodha_api_key)
    stats.allow_paid = user.allow_paid
    stats.risk_locked = bool(stats.risk_locked)

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


# Achievement definitions
ACHIEVEMENTS = [
    {"id": "first-blood", "name": "First Blood", "description": "Solve your first problem", "icon": "🎯", "rarity": "common", "check": lambda s: s.problems_solved >= 1},
    {"id": "week-warrior", "name": "Week Warrior", "description": "Maintain a 7-day streak", "icon": "🔥", "rarity": "rare", "check": lambda s: s.max_streak >= 7},
    {"id": "month-master", "name": "Month Master", "description": "Maintain a 30-day streak", "icon": "👑", "rarity": "epic", "check": lambda s: s.max_streak >= 30},
    {"id": "century-club", "name": "Century Club", "description": "Solve 100 problems", "icon": "💯", "rarity": "epic", "check": lambda s: s.problems_solved >= 100},
    {"id": "diamond-hands", "name": "Diamond Hands", "description": "Never trigger a penalty", "icon": "💎", "rarity": "legendary", "check": lambda s: s.lifetime_loss == 0 and s.problems_solved >= 10},
    {"id": "survivor", "name": "Survivor", "description": "Recover from 0 lives", "icon": "🛡️", "rarity": "rare", "check": lambda s: s.lives > 0 and s.problems_since_last_life > 0},
    {"id": "grinder", "name": "Grinder", "description": "Solve 50 problems", "icon": "⚡", "rarity": "rare", "check": lambda s: s.problems_solved >= 50},
    {"id": "dedicated", "name": "Dedicated", "description": "Solve 10 problems", "icon": "📚", "rarity": "common", "check": lambda s: s.problems_solved >= 10},
]


@router.get("/inventory", response_model=InventoryResponse)
def get_user_inventory(
    user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    inventory_items = db.query(UserInventory).filter(UserInventory.user_id == user.id).all()
    
    items = [
        InventoryItem(
            item_id=item.item_id,
            quantity=item.quantity,
            acquired_at=item.acquired_at
        )
        for item in inventory_items
    ]
    
    return InventoryResponse(items=items)


@router.get("/achievements", response_model=AchievementsResponse)
def get_user_achievements(
    user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stats = db.query(UserStat).filter(UserStat.user_id == user.id).first()
    unlocked_achievements = db.query(UserAchievement).filter(UserAchievement.user_id == user.id).all()
    unlocked_ids = {a.achievement_id: a.unlocked_at for a in unlocked_achievements}
    
    achievements = []
    for ach_def in ACHIEVEMENTS:
        is_unlocked = ach_def["id"] in unlocked_ids
        
        # Check if newly unlocked
        if stats and not is_unlocked and ach_def["check"](stats):
            # Unlock achievement
            new_ach = UserAchievement(user_id=user.id, achievement_id=ach_def["id"])
            db.add(new_ach)
            db.commit()
            is_unlocked = True
            unlocked_ids[ach_def["id"]] = new_ach.unlocked_at
        
        achievements.append(Achievement(
            id=ach_def["id"],
            name=ach_def["name"],
            description=ach_def["description"],
            icon=ach_def["icon"],
            rarity=ach_def["rarity"],
            unlocked=is_unlocked,
            unlocked_at=unlocked_ids.get(ach_def["id"])
        ))
    
    return AchievementsResponse(achievements=achievements)


POWERUPS = {
    "streak-freeze": {"name": "Streak Freeze", "cost": 150},
    "penalty-shield": {"name": "Penalty Shield", "cost": 250},
}

@router.post("/purchase-powerup", response_model=UserStatsResponse)
async def purchase_powerup(
    request: PowerupPurchaseRequest,
    user = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis = Depends(get_redis_client),
):
    powerup_id = request.powerup_id
    if powerup_id not in POWERUPS:
        raise HTTPException(status_code=400, detail="Powerup not found or coming soon")
        
    powerup = POWERUPS[powerup_id]
    stats = db.query(UserStat).filter(UserStat.user_id == user.id).first()
    
    if not stats or stats.gamcoins < powerup["cost"]:
        raise HTTPException(status_code=400, detail="Insufficient GamCoins")
        
    # Deduct coins
    stats.gamcoins -= powerup["cost"]
    
    # Add to inventory
    inventory_item = db.query(UserInventory).filter(
        UserInventory.user_id == user.id,
        UserInventory.item_id == powerup_id
    ).first()
    
    if inventory_item:
        inventory_item.quantity += 1
    else:
        new_item = UserInventory(user_id=user.id, item_id=powerup_id, quantity=1)
        db.add(new_item)
        
    db.commit()
    
    # Use existing get_user_stats logic
    return await get_user_stats(user, db, redis)
