import json
import os
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import distinct
from typing import Optional, List

from database import get_db
from dependencies import get_current_user
from models import Question, UserStat, QuestionCompletion

router = APIRouter(prefix="/problems", tags=["Problems"])

NEETCODE_150_PATH = os.path.join(os.path.dirname(__file__), "../content/neetcode-150.json")


@router.get("/all")
async def get_all_problems(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    difficulty: Optional[str] = None,
    topic: Optional[str] = None,
    search: Optional[str] = None,
    user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all problems with pagination and optional filters."""
    query = db.query(Question)
    
    # Apply filters
    if difficulty:
        query = query.filter(Question.difficulty == difficulty)
    if topic:
        query = query.filter(Question.topics.contains(topic))
    if search:
        query = query.filter(Question.title.ilike(f"%{search}%"))
    if user.allow_paid == 0:
        query = query.filter(Question.paid_only == 0)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * limit
    questions = query.order_by(Question.id).offset(offset).limit(limit).all()
    
    # Get completed question IDs for this user
    completed_ids = set()
    if questions:
        question_ids = [q.id for q in questions]
        completions = db.query(QuestionCompletion.question_id).filter(
            QuestionCompletion.user_id == user.id,
            QuestionCompletion.question_id.in_(question_ids)
        ).all()
        completed_ids = {c[0] for c in completions}
    
    return {
        "problems": [
            {
                "id": q.id,
                "title": q.title,
                "slug": q.slug,
                "difficulty": q.difficulty,
                "topics": q.topics,
                "acc_rate": q.acc_rate,
                "paid_only": q.paid_only,
                "completed": q.id in completed_ids
            }
            for q in questions
        ],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit
    }


@router.get("/topics")
async def get_topics(
    db: Session = Depends(get_db),
):
    """Get all unique topics from the questions table."""
    # Get all topics as a list of strings
    topics_rows = db.query(Question.topics).filter(Question.topics.isnot(None)).all()
    
    # Parse comma-separated topics and collect unique ones
    unique_topics = set()
    for row in topics_rows:
        if row[0]:
            for topic in row[0].split(", "):
                topic = topic.strip()
                if topic:
                    unique_topics.add(topic)
    
    return {"topics": sorted(unique_topics)}


@router.get("/sheets")
async def get_sheets():
    """Get available problem sheets."""
    return {
        "sheets": [
            {
                "id": "neetcode150",
                "name": "NeetCode 150",
                "description": "150 essential LeetCode problems for coding interviews",
                "problem_count": 150
            }
        ]
    }


@router.get("/sheets/neetcode150")
async def get_neetcode150(
    user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get NeetCode 150 problems mapped to database questions."""
    # Load NeetCode 150 JSON
    try:
        with open(NEETCODE_150_PATH, "r") as f:
            neetcode_data = json.load(f)
    except FileNotFoundError:
        return {"error": "NeetCode 150 data not found", "categories": {}}
    
    # Extract slugs from LeetCode URLs and map to DB
    result = {}
    all_slugs = []
    
    for category, problems in neetcode_data.items():
        result[category] = []
        for title, info in problems.items():
            # Extract slug from LeetCode URL
            url = info.get("url", "")
            slug = url.rstrip("/").split("/")[-1] if url else ""
            all_slugs.append(slug)
            result[category].append({
                "title": title,
                "slug": slug,
                "difficulty": info.get("difficulty", ""),
                "neetcode_url": info.get("nurl", ""),
                "leetcode_url": url
            })
    
    # Batch query to get completion status and DB IDs
    db_questions = db.query(Question.id, Question.slug).filter(
        Question.slug.in_(all_slugs)
    ).all()
    slug_to_id = {q.slug: q.id for q in db_questions}
    
    # Get user's completions
    completed_ids = set()
    if slug_to_id:
        completions = db.query(QuestionCompletion.question_id).filter(
            QuestionCompletion.user_id == user.id,
            QuestionCompletion.question_id.in_(slug_to_id.values())
        ).all()
        completed_ids = {c[0] for c in completions}
    
    # Add completion status and DB ID to results
    for category in result:
        for problem in result[category]:
            db_id = slug_to_id.get(problem["slug"])
            problem["id"] = db_id
            problem["completed"] = db_id in completed_ids if db_id else False
            problem["in_database"] = db_id is not None
    
    # Calculate stats
    total_problems = sum(len(probs) for probs in result.values())
    completed_count = sum(
        1 for cat in result.values() 
        for p in cat 
        if p.get("completed")
    )
    
    return {
        "categories": result,
        "stats": {
            "total": total_problems,
            "completed": completed_count,
            "percentage": round(completed_count / total_problems * 100, 1) if total_problems > 0 else 0
        }
    }


@router.post("/preference")
async def update_problem_set_preference(
    preference: dict,
    user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update user's problem set preference."""
    stats = db.query(UserStat).filter(UserStat.user_id == user.id).first()
    if not stats:
        stats = UserStat(user_id=user.id)
        db.add(stats)
    
    set_type = preference.get("type", "default")
    if set_type not in ["default", "topics", "sheet"]:
        set_type = "default"
    
    stats.problem_set_type = set_type
    
    if set_type == "topics":
        topics = preference.get("topics", [])
        stats.problem_set_topics = json.dumps(topics) if topics else None
        stats.problem_set_sheet = None
    elif set_type == "sheet":
        stats.problem_set_sheet = preference.get("sheet", "neetcode150")
        stats.problem_set_topics = None
    else:
        stats.problem_set_topics = None
        stats.problem_set_sheet = None
    
    db.commit()
    
    return {
        "success": True,
        "preference": {
            "type": stats.problem_set_type,
            "topics": json.loads(stats.problem_set_topics) if stats.problem_set_topics else None,
            "sheet": stats.problem_set_sheet
        }
    }


@router.get("/preference")
async def get_problem_set_preference(
    user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get user's current problem set preference."""
    stats = db.query(UserStat).filter(UserStat.user_id == user.id).first()
    
    if not stats:
        return {
            "type": "default",
            "topics": None,
            "sheet": None
        }
    
    return {
        "type": stats.problem_set_type or "default",
        "topics": json.loads(stats.problem_set_topics) if stats.problem_set_topics else None,
        "sheet": stats.problem_set_sheet
    }
