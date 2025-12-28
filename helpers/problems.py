import datetime
import random
from sqlalchemy.orm import Session
from models import Question, User

def get_curated_problems_for_user(db: Session, user: User, date_str: str = None):
    if date_str is None:
        date_str = datetime.date.today().isoformat()
        
    seed = int(date_str.replace("-", ""))
    random.seed(seed)

    result = {}
    difficulties = ["Easy", "Medium", "Hard"]

    for diff in difficulties:
        query = db.query(Question.id, Question.title, Question.slug, Question.topics, Question.difficulty, Question.paid_only).filter(Question.difficulty == diff)
        if user.allow_paid == 0:
            query = query.filter(Question.paid_only == 0)
        
        ids = [row[0] for row in query.all()]
        if not ids:
            result[diff.lower()] = None
            continue

        random_id = random.choice(ids)
        # We already have the info in the query above if we want, but let's be consistent
        question = db.query(Question).filter(Question.id == random_id).first()

        if question:
            result[diff.lower()] = {
                "id": question.id,
                "title": question.title,
                "slug": question.slug,
                "difficulty": question.difficulty,
                "topics": question.topics,
                "paid_only": question.paid_only
            }
        else:
            result[diff.lower()] = None
            
    return result
