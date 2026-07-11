from fastapi import APIRouter, status, Depends, Query, BackgroundTasks
from api.tutorials import schemas, service
from core.dependencies import get_current_user

router = APIRouter(prefix="/tutorials", tags=["Tutorials"])

@router.post("", response_model=schemas.TutorialResponse, status_code=status.HTTP_201_CREATED)
async def create_tutorial(
    tutorial_in: schemas.TutorialCreate, 
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    user_id = str(current_user["_id"])
    return await service.create_tutorial(user_id, tutorial_in, background_tasks)

@router.get("", response_model=schemas.PaginatedTutorials, status_code=status.HTTP_200_OK)
async def get_tutorials(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    user_id = str(current_user["_id"])
    return await service.get_user_tutorials(user_id, skip, limit)

@router.patch("/{tutorial_id}", status_code=status.HTTP_200_OK)
async def update_tutorial(
    tutorial_id: str, 
    tutorial_in: schemas.TutorialUpdate, 
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    user_id = str(current_user["_id"])
    return await service.update_tutorial(user_id, tutorial_id, tutorial_in, background_tasks)

@router.patch("/{tutorial_id}/assign", status_code=status.HTTP_200_OK)
async def assign_tutorial(
    tutorial_id: str, 
    assign_data: schemas.TutorialAssignGroup, 
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    user_id = str(current_user["_id"])
    return await service.assign_tutorial_to_group(user_id, tutorial_id, assign_data, background_tasks)

@router.delete("/{tutorial_id}", status_code=status.HTTP_200_OK)
async def delete_tutorial(
    tutorial_id: str, 
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    user_id = str(current_user["_id"])
    return await service.delete_tutorial(user_id, tutorial_id, background_tasks)

@router.get("/group/{group_id}", response_model=schemas.PaginatedTutorials, status_code=status.HTTP_200_OK)
async def get_tutorials_by_group(
    group_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    return await service.get_tutorials_by_group(group_id, skip, limit)

@router.get("/subgroup/{subgroup_id}", response_model=schemas.PaginatedTutorials, status_code=status.HTTP_200_OK)
async def get_tutorials_by_subgroup(
    subgroup_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    return await service.get_tutorials_by_subgroup(subgroup_id, skip, limit)

@router.get("/by-url", response_model=schemas.TutorialResponse, status_code=status.HTTP_200_OK)
async def get_tutorial_by_url(
    url: str,
    current_user: dict = Depends(get_current_user)
):
    user_id = str(current_user["_id"])
    return await service.get_tutorial_by_url(user_id, url)
