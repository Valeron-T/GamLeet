from pydantic import BaseModel
from typing import Optional, List


class LeetCodeSubmissionItem(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    slug: Optional[str] = None
    status: Optional[str] = None
    timestamp: Optional[int] = None
    url: Optional[str] = None
    in_database: bool = False
    question_id: Optional[int] = None
    gamleet_synced: bool = False
    sync_source: Optional[str] = None


class LeetCodeSubmissionsResponse(BaseModel):
    submissions: List[LeetCodeSubmissionItem]


class LeetCodeSubmissionSyncResponse(BaseModel):
    synced: int
    updated: int = 0
    total: int = 0
