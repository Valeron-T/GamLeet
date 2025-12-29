from pydantic import BaseModel
from decimal import Decimal
from datetime import date, datetime
from typing import Optional

class UserStatsResponse(BaseModel):
    lifetime_loss: Decimal
    available_balance: Decimal
    current_streak: int
    max_streak: int
    problems_solved: int
    problems_since_last_life: int
    lives: int
    difficulty_mode: str
    powerups_used_today: int
    gamcoins: int
    total_xp: int
    name: Optional[str] = None
    email: Optional[str] = None
    leetcode_connected: bool = False
    leetcode_username: Optional[str] = None
    zerodha_connected: bool = False
    allow_paid: int = 0
    zerodha_error: Optional[str] = None
    last_activity_date: Optional[date] = None

    class Config:
        orm_mode = True

class DifficultyUpdateRequest(BaseModel):
    difficulty_mode: str
