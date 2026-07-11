from fastapi import APIRouter, status, Depends, Query, File, UploadFile, Form, HTTPException, BackgroundTasks
from typing import List, Optional
from api.notes import schemas, service
from core.dependencies import get_current_user
from core.blob import upload_file_to_bucket

router = APIRouter(prefix="/notes", tags=["Notes"])

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

@router.post("", response_model=schemas.NoteResponse, status_code=status.HTTP_201_CREATED)
async def create_note(
    background_tasks: BackgroundTasks,
    tutorial_id: str = Form(...),
    note_content: Optional[str] = Form(None),
    timestamp: Optional[str] = Form(None),
    media: List[UploadFile] = File(default=[]),
    current_user: dict = Depends(get_current_user)
):
    user_id = str(current_user["_id"])
    
    media_urls = []
    
    # Process files
    for file in media:
        if file.size and file.size > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail=f"File {file.filename} is too large. Max size is 5MB.")
            
        # Optional: check actual file size by seeking if file.size is None
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail=f"File {file.filename} is too large. Max size is 5MB.")
            
        # Reset file pointer after reading
        await file.seek(0)
        
        url = await upload_file_to_bucket(file)
        if url:
            media_urls.append(url)
        else:
            raise HTTPException(status_code=500, detail=f"Failed to upload {file.filename}")
            
    return await service.create_note(user_id, tutorial_id, note_content, media_urls, timestamp, background_tasks)

@router.patch("/{note_id}", status_code=status.HTTP_200_OK)
async def update_note(
    note_id: str, 
    note_content: Optional[str] = Form(None),
    media_to_keep: List[str] = Form(default=[]),
    new_media: List[UploadFile] = File(default=[]),
    current_user: dict = Depends(get_current_user)
):
    user_id = str(current_user["_id"])
    
    new_media_urls = []
    
    # Process new files
    for file in new_media:
        if file.size and file.size > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail=f"File {file.filename} is too large. Max size is 5MB.")
            
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail=f"File {file.filename} is too large. Max size is 5MB.")
            
        await file.seek(0)
        url = await upload_file_to_bucket(file)
        if url:
            new_media_urls.append(url)
        else:
            raise HTTPException(status_code=500, detail=f"Failed to upload {file.filename}")

    return await service.update_note(user_id, note_id, note_content, media_to_keep, new_media_urls)

@router.delete("/{note_id}", status_code=status.HTTP_200_OK)
async def delete_note(
    note_id: str, 
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    user_id = str(current_user["_id"])
    return await service.delete_note(user_id, note_id, background_tasks)

@router.get("/tutorial/{tutorial_id}", response_model=schemas.PaginatedNotes, status_code=status.HTTP_200_OK)
async def get_notes_by_tutorial(
    tutorial_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    user_id = str(current_user["_id"])
    return await service.get_notes_by_tutorial(user_id, tutorial_id, skip, limit)
