import json
import os
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import distinct
from typing import Optional, List

from database import get_db
from dependencies import get_current_user
from models import Question, UserStat, QuestionCompletion, LeetCodeSubmission
from schemas.manual_sync import ManualSyncResponse
from schemas.leetcode_submissions import LeetCodeSubmissionsResponse, LeetCodeSubmissionItem, LeetCodeSubmissionSyncResponse

router = APIRouter(prefix="/problems", tags=["Problems"])

NEETCODE_150_PATH = os.path.join(os.path.dirname(__file__), "../content/neetcode-150.json")


def _month_bounds(month: str | None):
    now = datetime.now(timezone.utc)
    target = now
    if month:
        try:
            year_str, month_str = month.split("-", 1)
            target = datetime(int(year_str), int(month_str), 1, tzinfo=timezone.utc)
        except Exception:
            raise HTTPException(status_code=400, detail="month must be in YYYY-MM format")

    month_start = datetime(target.year, target.month, 1, tzinfo=timezone.utc)
    if target.month == 12:
        next_month = datetime(target.year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        next_month = datetime(target.year, target.month + 1, 1, tzinfo=timezone.utc)

    return now, month_start, next_month


def _lookback_month_start(months: int):
    now = datetime.now(timezone.utc)
    year = now.year
    month = now.month

    for _ in range(months - 1):
        if month == 1:
            year -= 1
            month = 12
        else:
            month -= 1

    return now, datetime(year, month, 1, tzinfo=timezone.utc)


def _parse_progress_timestamp(value) -> int:
    if value is None or value == "":
        return 0

    if isinstance(value, (int, float)):
        return int(value)

    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            try:
                return int(datetime.fromisoformat(value).timestamp())
            except ValueError:
                return 0

    return 0


async def _sync_leetcode_submission_history(user, db: Session, since_timestamp: int | None = None):
    from helpers.leetcode import fetch_all_submissions

    if not user.leetcode_username or not user.leetcode_session:
        return 0, 0, 0

    submissions = await fetch_all_submissions(
        username=user.leetcode_username,
        session=user.leetcode_session,
        since_timestamp=since_timestamp,
    )

    if not submissions:
        return 0, 0, 0

    existing_ids = {
        row[0]
        for row in db.query(LeetCodeSubmission.submission_id)
        .filter(LeetCodeSubmission.user_id == user.id)
        .all()
    }

    synced = 0
    updated = 0

    for item in submissions:
        submission_id = str(item.get("id") or "").strip()
        if not submission_id:
            continue

        if submission_id in existing_ids:
            continue

        db.add(
            LeetCodeSubmission(
                user_id=user.id,
                submission_id=submission_id,
                title=item.get("title"),
                slug=item.get("slug"),
                status=item.get("status"),
                timestamp=item.get("timestamp"),
            )
        )
        existing_ids.add(submission_id)
        synced += 1

    if synced > 0:
        db.commit()
    else:
        db.rollback()

    return synced, updated, len(submissions)


def _serialize_submission_row(row: LeetCodeSubmission, slug_to_id: dict[str, int], completion_map: dict[int, str | None]):
    question_id = slug_to_id.get(row.slug or "")
    sync_source = completion_map.get(question_id) if question_id else None
    return LeetCodeSubmissionItem(
        id=row.submission_id,
        title=row.title,
        slug=row.slug,
        status=row.status,
        timestamp=row.timestamp,
        url=f"https://leetcode.com/problems/{row.slug}/" if row.slug else None,
        in_database=question_id is not None,
        question_id=question_id,
        gamleet_synced=sync_source is not None,
        sync_source=sync_source,
    )


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
        from sqlalchemy import func
        query = query.filter(func.lower(Question.difficulty) == difficulty.lower())
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


@router.post("/sync-history", response_model=ManualSyncResponse)
async def sync_leetcode_history(
    months: Optional[int] = Query(None, ge=1, le=36, description="How many recent months of solved problems to sync"),
    user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sync solved problems from the last N months without awarding XP/coins twice."""
    from helpers.leetcode import fetch_solved_problem_progress
    from fastapi import HTTPException

    if not user.leetcode_username:
        raise HTTPException(status_code=400, detail="LeetCode username not configured")

    cutoff_ts = None
    if months is not None:
        _, month_start = _lookback_month_start(months)
        cutoff_ts = int(month_start.timestamp())

    progress_rows = await fetch_solved_problem_progress(
        username=user.leetcode_username,
        session=user.leetcode_session,
    )

    if not progress_rows:
        return ManualSyncResponse(synced=0, skipped=0, unmatched=0)

    solved_rows = [
        row
        for row in progress_rows
        if cutoff_ts is None or _parse_progress_timestamp(row.get("lastSubmittedAt")) >= cutoff_ts
    ]

    if not solved_rows:
        return ManualSyncResponse(synced=0, skipped=0, unmatched=0)

    slugs = [row.get("titleSlug") for row in solved_rows if row.get("titleSlug")]
    db_questions = db.query(Question.id, Question.slug).filter(
        Question.slug.in_(slugs)
    ).all()
    slug_to_id = {q.slug: q.id for q in db_questions}
    unmatched = len([slug for slug in slugs if slug not in slug_to_id])

    matched_ids = list(slug_to_id.values())
    existing_completions = set()
    if matched_ids:
        existing = db.query(QuestionCompletion.question_id).filter(
            QuestionCompletion.user_id == user.id,
            QuestionCompletion.question_id.in_(matched_ids)
        ).all()
        existing_completions = {c[0] for c in existing}

    synced = 0
    skipped = 0
    for row in solved_rows:
        slug = row.get("titleSlug")
        if not slug:
            continue

        qid = slug_to_id.get(slug)
        if not qid:
            continue

        if qid in existing_completions:
            skipped += 1
            continue

        completion = QuestionCompletion(
            user_id=user.id,
            question_id=qid,
            source="manual",
        )
        db.add(completion)
        existing_completions.add(qid)
        synced += 1

    if synced > 0:
        stats = db.query(UserStat).filter(UserStat.user_id == user.id).first()
        if stats:
            stats.problems_solved += synced
        db.commit()
    else:
        db.rollback()

    return ManualSyncResponse(synced=synced, skipped=skipped, unmatched=unmatched)


@router.post("/sync-leetcode-submissions", response_model=LeetCodeSubmissionSyncResponse)
async def sync_leetcode_submissions(
    months: Optional[int] = Query(None, ge=1, le=36, description="Look back N months from the current month"),
    user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Backfill and incrementally sync raw LeetCode submissions into local storage."""
    since_timestamp = None
    if months is not None:
        _, month_start = _lookback_month_start(months)
        since_timestamp = int(month_start.timestamp())

    synced, updated, total = await _sync_leetcode_submission_history(user, db, since_timestamp=since_timestamp)
    from helpers.leetcode import recalculate_user_streak
    recalculate_user_streak(user.id, db)
    return LeetCodeSubmissionSyncResponse(synced=synced, updated=updated, total=total)


@router.get("/leetcode-submissions", response_model=LeetCodeSubmissionsResponse)
async def get_leetcode_submissions(
    limit: int = Query(20, ge=1, le=100),
    month: Optional[str] = Query(None, description="Month to filter in YYYY-MM format"),
    months: Optional[int] = Query(None, ge=1, le=36, description="Look back N months from the current month"),
    user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Read cached submissions, backfilling from LeetCode when the cache is empty."""

    if not user.leetcode_username:
        return LeetCodeSubmissionsResponse(submissions=[])

    now = datetime.now(timezone.utc)
    since_timestamp: int | None = None
    if months is not None:
        _, month_start = _lookback_month_start(months)
        since_timestamp = int(month_start.timestamp())
        query_start = month_start
        query_end = now
    else:
        _, month_start, next_month = _month_bounds(month)
        query_start = month_start
        query_end = next_month if month else now
        since_timestamp = int(query_start.timestamp()) if month else None

    query = db.query(LeetCodeSubmission).filter(LeetCodeSubmission.user_id == user.id)
    if month or months is not None:
        query = query.filter(
            LeetCodeSubmission.timestamp.isnot(None),
            LeetCodeSubmission.timestamp >= int(query_start.timestamp()),
            LeetCodeSubmission.timestamp < int(query_end.timestamp()),
        )

    order_clause = (
        LeetCodeSubmission.timestamp.is_(None),
        LeetCodeSubmission.timestamp.desc(),
        LeetCodeSubmission.id.desc(),
    )
    rows = query.order_by(*order_clause).limit(limit).all()

    if not rows:
        # Backfill before giving up so the first visit can hydrate older history.
        await _sync_leetcode_submission_history(user, db, since_timestamp=since_timestamp)
        rows = query.order_by(*order_clause).limit(limit).all()

    slugs = [row.slug for row in rows if row.slug]
    db_questions = db.query(Question.id, Question.slug).filter(
        Question.slug.in_(slugs)
    ).all() if slugs else []
    slug_to_id = {q.slug: q.id for q in db_questions}

    question_ids = list(slug_to_id.values())
    completion_map = {}
    if question_ids:
        completions = db.query(
            QuestionCompletion.question_id,
            QuestionCompletion.source,
        ).filter(
            QuestionCompletion.user_id == user.id,
            QuestionCompletion.question_id.in_(question_ids),
        ).all()
        completion_map = {question_id: source for question_id, source in completions}

    submissions = [
        _serialize_submission_row(row, slug_to_id, completion_map)
        for row in rows
    ]

    return LeetCodeSubmissionsResponse(submissions=submissions)
