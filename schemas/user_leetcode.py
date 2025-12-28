from pydantic import BaseModel
from typing import Optional

class LeetCodeUpdate(BaseModel):
    username: str
    session: str
    allow_paid: Optional[int] = 0
