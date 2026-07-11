from pydantic import BaseModel
from typing import Optional

class RewriteRequest(BaseModel):
    text: str
    context: str = "general"

class RewriteResponse(BaseModel):
    original_text: str
    rewritten_text: str
    improvement_applied: bool

class STTResponse(BaseModel):
    text: str
