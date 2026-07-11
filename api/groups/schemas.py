from pydantic import BaseModel, Field
from typing import List
from datetime import datetime

class PaginationMeta(BaseModel):
    total: int
    skip: int
    limit: int

class GroupCreate(BaseModel):
    group_name: str = Field(..., min_length=1, max_length=100)

class GroupUpdate(BaseModel):
    group_name: str = Field(..., min_length=1, max_length=100)

class SubGroupCreate(BaseModel):
    subgroup_name: str = Field(..., min_length=1, max_length=100)

class SubGroupUpdate(BaseModel):
    subgroup_name: str = Field(..., min_length=1, max_length=100)

class SubGroupResponse(BaseModel):
    id: str
    group_id: str
    subgroup_name: str
    created_at: datetime
    last_updated: datetime
    number_of_tutorials: int
    number_of_notes: int

class GroupResponse(BaseModel):
    id: str
    user_id: str
    group_name: str
    created_at: datetime
    last_updated: datetime
    number_of_tutorials: int
    number_of_notes: int
    number_of_subgroups: int

class GroupWithSubgroupsResponse(GroupResponse):
    subgroups: List[SubGroupResponse]

class SubGroupNameResponse(BaseModel):
    id: str
    subgroup_name: str

class GroupNameResponse(BaseModel):
    id: str
    group_name: str
    subgroups: List[SubGroupNameResponse]

class PaginatedGroups(BaseModel):
    meta: PaginationMeta
    data: List[GroupWithSubgroupsResponse]

class PaginatedSubGroups(BaseModel):
    meta: PaginationMeta
    data: List[SubGroupResponse]
