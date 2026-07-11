from fastapi import APIRouter, status, Depends, Query
from api.chats import schemas, service
from core.dependencies import get_current_user

router = APIRouter(prefix="/chats", tags=["Chats"])

@router.post("/tutorial/{tutorial_id}", response_model=schemas.ChatResponse, status_code=status.HTTP_201_CREATED)
async def send_chat_message(
    tutorial_id: str, 
    chat_in: schemas.ChatRequest, 
    current_user: dict = Depends(get_current_user)
):
    """Send a message to the AI companion for a specific tutorial."""
    user_id = str(current_user["_id"])
    return await service.process_chat(user_id, tutorial_id, chat_in.message, chat_in.current_timestamp)

@router.get("/tutorial/{tutorial_id}", response_model=schemas.PaginatedChats, status_code=status.HTTP_200_OK)
async def get_chat_history(
    tutorial_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """Retrieve paginated chat history for a tutorial."""
    user_id = str(current_user["_id"])
    return await service.get_chat_history(user_id, tutorial_id, skip, limit)
