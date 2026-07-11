from pydantic import BaseModel
from typing import List, Optional, Union
from datetime import datetime

class ChatRequest(BaseModel):
    message: str
    current_timestamp: Optional[Union[float, str]] = None

class ChatEntry(BaseModel):
    user: str
    ai: str
    created_at: datetime

class ChatResponse(BaseModel):
    id: str
    tutorial_id: str
    user: str
    ai: str
    created_at: datetime

class PaginatedChats(BaseModel):
    meta: dict
    data: List[ChatResponse]
