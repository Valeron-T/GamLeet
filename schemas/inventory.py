from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class InventoryItem(BaseModel):
    item_id: str
    quantity: int
    acquired_at: Optional[datetime] = None


class InventoryResponse(BaseModel):
    items: List[InventoryItem]


class Achievement(BaseModel):
    id: str
    name: str
    description: str
    icon: str
    rarity: str  # common, rare, epic, legendary
    unlocked: bool
    unlocked_at: Optional[datetime] = None
    progress: Optional[int] = None  # For incremental achievements
    target: Optional[int] = None


class AchievementsResponse(BaseModel):
    achievements: List[Achievement]
