from pydantic import BaseModel
from typing import List

class DailyActivity(BaseModel):
    date: str  # YYYY-MM-DD
    count: int

class ActivityGraphResponse(BaseModel):
    activity: List[DailyActivity]
    total_solved: int
