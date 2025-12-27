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
    redis: redis.Redis = Depends(get_redis_client),
):
    today = datetime.date.today().isoformat()
    # Deterministic randomness (same per day)
    seed = int(today.replace("-", ""))
    random.seed(seed)

    result = {}
    difficulties = ["Easy", "Medium", "Hard"]

    for diff in difficulties:
        # Fetch all IDs of this difficulty once
        ids = [row[0] for row in db.query(Question.id).filter(Question.difficulty == diff).all()]
        if not ids:
            result[diff.lower()] = None
            continue

        random_id = random.choice(ids)
        question = (
            db.query(
                Question.id,
                Question.title,
                Question.slug,
                Question.acc_rate,
                Question.paid_only,
                Question.difficulty,
                Question.topics,
            )
            .filter(Question.id == random_id)
            .first()
        )

        if question:
            q_dict = question._asdict()
            # convert decimals safely
            for k, v in q_dict.items():
                if isinstance(v, Decimal):
                    q_dict[k] = float(v)
            result[diff.lower()] = q_dict
        else:
            result[diff.lower()] = None

    response = {"date": today, "problems": result}

    # Dynamic status check (not cached globally)
    from helpers.leetcode import get_problems_status
    slugs = [p["slug"] for p in result.values() if p and "slug" in p]
    if slugs:
        status_map = get_problems_status(slugs, username=user.leetcode_username, session=user.leetcode_session)
        for key in result:
            if result[key] and "slug" in result[key]:
                result[key]["status"] = status_map.get(result[key]["slug"], "unattempted")

    return response
