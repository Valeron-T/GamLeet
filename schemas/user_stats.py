from pydantic import BaseModel
from decimal import Decimal
from datetime import date
from typing import Optional

class UserStatsResponse(BaseModel):
    lifetime_loss: Decimal
    available_balance: Decimal
    current_streak: int
    max_streak: int
    problems_solved: int
    gamcoins: int
    total_xp: int


    last_activity_date: Optional[date]

    class Config:
        orm_mode = True
