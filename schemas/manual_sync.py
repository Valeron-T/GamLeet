from pydantic import BaseModel


class ManualSyncResponse(BaseModel):
    synced: int       # newly added completions
    skipped: int      # already existed (duplicates)
    unmatched: int    # slugs not found in our questions DB
