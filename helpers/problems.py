import datetime
import json
import os
import random
from sqlalchemy.orm import Session
from models import Question, User, UserStat

NEETCODE_150_PATH = os.path.join(os.path.dirname(__file__), "../content/neetcode-150.json")


def get_neetcode150_slugs():
    """Load NeetCode 150 slugs from JSON file."""
    try:
        with open(NEETCODE_150_PATH, "r") as f:
            data = json.load(f)
        slugs = []
        for category, problems in data.items():
            for title, info in problems.items():
                url = info.get("url", "")
                slug = url.rstrip("/").split("/")[-1] if url else ""
                if slug:
                    slugs.append(slug)
        return slugs
    except Exception:
        return []


def get_curated_problems_for_user(db: Session, user: User, date_str: str = None):
    if date_str is None:
        date_str = datetime.date.today().isoformat()
        
    seed = int(date_str.replace("-", ""))
    random.seed(seed)

    # Get user's problem set preferences
    stats = db.query(UserStat).filter(UserStat.user_id == user.id).first()
    problem_set_type = stats.problem_set_type if stats else "default"
    problem_set_topics = None
    problem_set_sheet = None
    
    if stats and stats.problem_set_topics:
        try:
            problem_set_topics = json.loads(stats.problem_set_topics)
        except json.JSONDecodeError:
            problem_set_topics = None
    
    if stats:
        problem_set_sheet = stats.problem_set_sheet

    # 1. Build the pool of eligible questions
    query = db.query(Question.id, Question.title, Question.slug, Question.topics, Question.difficulty, Question.paid_only)
    
    if user.allow_paid == 0:
        query = query.filter(Question.paid_only == 0)
        
    if problem_set_type == "sheet" and problem_set_sheet == "neetcode150":
        neetcode_slugs = get_neetcode150_slugs()
        if neetcode_slugs:
            query = query.filter(Question.slug.in_(neetcode_slugs))
    elif problem_set_type == "topics" and problem_set_topics:
        from sqlalchemy import or_
        topic_conditions = [Question.topics.contains(topic) for topic in problem_set_topics]
        if topic_conditions:
            query = query.filter(or_(*topic_conditions))

    all_eligible = query.all()
    
    # 2. Pick 3 questions
    selected_questions = []
    
    def q_to_dict(q):
        if not q:
            return None
        return {
            "id": q.id,
            "title": q.title,
            "slug": q.slug,
            "difficulty": q.difficulty,
            "topics": q.topics,
            "paid_only": q.paid_only
        }

    if not all_eligible:
        return {"easy": None, "medium": None, "hard": None}

    if problem_set_type == "sheet":
        # Random pick 3 from all eligible
        if len(all_eligible) >= 3:
            selected_questions = random.sample(all_eligible, 3)
        else:
            selected_questions = list(all_eligible)
            while len(selected_questions) < 3 and selected_questions:
                selected_questions.append(random.choice(all_eligible))
    else:
        # Default or Topics -> try 1 of each difficulty
        by_diff = {"Easy": [], "Medium": [], "Hard": []}
        for q in all_eligible:
            if q.difficulty in by_diff:
                by_diff[q.difficulty].append(q)
            elif q.difficulty == "Med": # Handle inconsistencies if any
                by_diff["Medium"].append(q)
        
        # Try to pick 1 from each
        temp_selected = [None, None, None]
        diffs = ["Easy", "Medium", "Hard"]
        
        for i, diff in enumerate(diffs):
            if by_diff[diff]:
                q = random.choice(by_diff[diff])
                temp_selected[i] = q
                by_diff[diff].remove(q)
        
        # Fill None placeholders from remaining pool
        remaining_pool = [q for diff_list in by_diff.values() for q in diff_list]
        for i in range(3):
            if temp_selected[i] is None and remaining_pool:
                q = random.choice(remaining_pool)
                temp_selected[i] = q
                remaining_pool.remove(q)
        
        # Last resort: if we still don't have 3 (pool was very small), just repeat
        while None in temp_selected and all_eligible:
            idx = temp_selected.index(None)
            temp_selected[idx] = random.choice(all_eligible)
            
        selected_questions = temp_selected

    # 3. Construct result
    return {
        "easy": q_to_dict(selected_questions[0]) if len(selected_questions) > 0 else None,
        "medium": q_to_dict(selected_questions[1]) if len(selected_questions) > 1 else None,
        "hard": q_to_dict(selected_questions[2]) if len(selected_questions) > 2 else None
    }

