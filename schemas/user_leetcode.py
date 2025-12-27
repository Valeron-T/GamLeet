from pydantic import BaseModel
from typing import Optional

class LeetCodeUpdate(BaseModel):
    username: str
    session: str
