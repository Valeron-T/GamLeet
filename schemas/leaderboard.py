from pydantic import BaseModel
from typing import List, Optional

class LeaderboardEntry(BaseModel):
    rank: int
    name: str
    total_xp: int
    problems_solved: int
    current_streak: int
    public_id: str

class LeaderboardResponse(BaseModel):
    entries: List[LeaderboardEntry]
