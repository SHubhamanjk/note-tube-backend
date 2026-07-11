from fastapi import APIRouter, status, Depends, Query, BackgroundTasks
from typing import List
from api.groups import schemas, service
from core.dependencies import get_current_user

router = APIRouter(prefix="/groups", tags=["Groups"])

@router.post("", response_model=schemas.GroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(
    group_in: schemas.GroupCreate, 
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    user_id = str(current_user["_id"])
    return await service.create_group(user_id, group_in, background_tasks)

@router.get("", response_model=schemas.PaginatedGroups, status_code=status.HTTP_200_OK)
async def get_groups(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    user_id = str(current_user["_id"])
    return await service.get_user_groups(user_id, skip, limit)

@router.get("/meta", response_model=List[schemas.GroupNameResponse], status_code=status.HTTP_200_OK)
async def get_group_names(current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["_id"])
    return await service.get_user_group_names(user_id)

@router.post("/{group_id}/subgroups", response_model=schemas.SubGroupResponse, status_code=status.HTTP_201_CREATED)
async def create_subgroup(
    group_id: str,
    subgroup_in: schemas.SubGroupCreate,
    current_user: dict = Depends(get_current_user)
):
    return await service.create_subgroup(group_id, subgroup_in)

@router.get("/{group_id}/subgroups", response_model=schemas.PaginatedSubGroups, status_code=status.HTTP_200_OK)
async def get_subgroups(
    group_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    return await service.get_subgroups_for_group(group_id, skip, limit)

@router.get("/{group_id}/subgroups/meta", response_model=List[schemas.SubGroupNameResponse], status_code=status.HTTP_200_OK)
async def get_subgroup_names(group_id: str, current_user: dict = Depends(get_current_user)):
    return await service.get_subgroup_names(group_id)

@router.patch("/{group_id}", status_code=status.HTTP_200_OK)
async def update_group(group_id: str, group_in: schemas.GroupUpdate, current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["_id"])
    return await service.update_group(user_id, group_id, group_in)

@router.delete("/{group_id}", status_code=status.HTTP_200_OK)
async def delete_group(
    group_id: str, 
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    user_id = str(current_user["_id"])
    return await service.delete_group(user_id, group_id, background_tasks)

@router.patch("/{group_id}/subgroups/{subgroup_id}", status_code=status.HTTP_200_OK)
async def update_subgroup(group_id: str, subgroup_id: str, subgroup_in: schemas.SubGroupUpdate, current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["_id"])
    return await service.update_subgroup(user_id, group_id, subgroup_id, subgroup_in)

@router.delete("/{group_id}/subgroups/{subgroup_id}", status_code=status.HTTP_200_OK)
async def delete_subgroup(group_id: str, subgroup_id: str, current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["_id"])
    return await service.delete_subgroup(user_id, group_id, subgroup_id)
