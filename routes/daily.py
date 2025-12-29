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

    # 2. Check status via database (Only shows as completed if synced)
    from models import QuestionCompletion
    question_ids = [p["id"] for p in result.values() if p and "id" in p]
    
    completions = []
    if question_ids:
        completions = db.query(QuestionCompletion.question_id).filter(
            QuestionCompletion.user_id == user.id,
            QuestionCompletion.question_id.in_(question_ids)
        ).all()
        
    completed_ids = {c[0] for c in completions}

    # Apply status to results
    for key in result:
        if result[key] and "id" in result[key]:
            is_completed = result[key]["id"] in completed_ids
            result[key]["status"] = "completed" if is_completed else "unattempted"

    return {"date": today, "problems": result}
