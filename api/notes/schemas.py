from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from api.groups.schemas import PaginationMeta

class NoteUpdate(BaseModel):
    note_content: Optional[str] = None
    # We will assume media is added via a separate endpoint if needed, or we just allow content update for now.

class NoteResponse(BaseModel):
    id: str
    user_id: str
    tutorial_id: str
    note_content: Optional[str] = None
    media: List[str] = []
    timestamp: Optional[str] = None # Or float depending on how frontend sends video timestamps
    created_at: datetime
    updated_at: datetime

class PaginatedNotes(BaseModel):
    meta: PaginationMeta
    data: List[NoteResponse]
