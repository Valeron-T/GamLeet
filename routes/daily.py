import datetime
from decimal import Decimal
import random
import json
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from models import Question
from database import get_db
from dependencies import get_redis_client, get_current_user
import redis.asyncio as redis

router = APIRouter()

def json_safe(obj):
    """Convert Decimal and other non-serializable types."""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Type {type(obj)} not serializable")

@router.get("/daily-questions")
async def get_daily_questions(
    user = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis_conn: redis.Redis = Depends(get_redis_client),
):
    today = datetime.date.today().isoformat()
    
    # 1. Try to get questions from cache
    # Include allow_paid in cache key since it changes the result set
    cache_key = f"daily_questions:{today}:paid_{user.allow_paid}"
    cached_questions = await redis_conn.get(cache_key)
    
    if cached_questions:
        result = json.loads(cached_questions)
    else:
        from helpers.problems import get_curated_problems_for_user
        result = get_curated_problems_for_user(db, user, today)
        
        # Save to cache for 24 hours
        await redis_conn.setex(cache_key, 86400, json.dumps(result))

    # 2. Dynamic status check (cached per user for 2 minutes)
    user_status_cache_key = f"user_status:{user.public_id}:{today}"
    cached_status = await redis_conn.get(user_status_cache_key)
    
    if cached_status:
        status_map = json.loads(cached_status)
    else:
        from helpers.leetcode import get_problems_status_async
        slugs = [p["slug"] for p in result.values() if p and "slug" in p]
        if slugs:
            # This is the slow part, we cache it
            status_map = await get_problems_status_async(slugs, username=user.leetcode_username, session=user.leetcode_session)
            await redis_conn.setex(user_status_cache_key, 120, json.dumps(status_map))
        else:
            status_map = {}

    # Apply status to results
    for key in result:
        if result[key] and "slug" in result[key]:
            result[key]["status"] = status_map.get(result[key]["slug"], "unattempted")

    return {"date": today, "problems": result}
