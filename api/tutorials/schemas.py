from pydantic import BaseModel, HttpUrl
from typing import Optional, List
from datetime import datetime
from api.groups.schemas import PaginationMeta
from datetime import datetime

class TutorialCreate(BaseModel):
    url: HttpUrl
    title: str
    group_id: Optional[str] = None
    subgroup_id: Optional[str] = None
class TutorialUpdate(BaseModel):
    title: Optional[str] = None
    group_id: Optional[str] = None
    subgroup_id: Optional[str] = None

class TutorialAssignGroup(BaseModel):
    group_id: str
    subgroup_id: Optional[str] = None

class TutorialResponse(BaseModel):
    id: str
    user_id: str
    url: str
    title: str
    created_at: datetime
    updated_at: datetime
    number_of_notes: int
    group_id: Optional[str] = None
    subgroup_id: Optional[str] = None

class PaginatedTutorials(BaseModel):
    meta: PaginationMeta
    data: List[TutorialResponse]
