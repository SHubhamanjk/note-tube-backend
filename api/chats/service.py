from fastapi import HTTPException
from bson import ObjectId
from core.database import get_chat_collection, get_tutorial_collection, get_note_collection
from core.utils import get_ist_now
from core.llm import chat_completion_with_fallback
from core.prompts import TUTORIAL_AI_COMPANION_PROMPT
from typing import List, Dict, Any
import re
async def verify_tutorial_ownership(user_id: str, tutorial_id: str) -> dict:
    print(f"[Chats] Verifying ownership of tutorial {tutorial_id} for user {user_id}")
    tutorials = get_tutorial_collection()
    try:
        obj_id = ObjectId(tutorial_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid tutorial ID")
        
    tutorial = await tutorials.find_one({"_id": obj_id, "user_id": user_id})
    if not tutorial:
        raise HTTPException(status_code=404, detail="Tutorial not found or permission denied")
    return tutorial

from typing import Union

async def process_chat(user_id: str, tutorial_id: str, message: str, current_timestamp: Union[float, str] = None) -> dict:
    if isinstance(current_timestamp, str):
        try:
            parts = current_timestamp.split(':')
            if len(parts) == 2:
                current_timestamp = float(parts[0]) * 60 + float(parts[1])
            elif len(parts) == 3:
                current_timestamp = float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
            else:
                current_timestamp = float(current_timestamp)
        except (ValueError, TypeError):
            current_timestamp = None
    print(f"[Chats] Processing chat for tutorial {tutorial_id}, user {user_id}. Timestamp: {current_timestamp}")
    tutorial = await verify_tutorial_ownership(user_id, tutorial_id)
    
    chats = get_chat_collection()
    notes_coll = get_note_collection()
    
    # 1. Fetch recent chat history
    recent_chats_cursor = chats.find({"tutorial_id": tutorial_id, "user_id": user_id}).sort("created_at", -1).limit(10)
    recent_chats_list = await recent_chats_cursor.to_list(length=10)
    # Reverse to make it chronological
    recent_chats_list.reverse()
    
    # 2. Fetch tutorial notes for context
    notes_cursor = notes_coll.find({"tutorial_id": tutorial_id, "user_id": user_id}).sort("created_at", 1)
    notes_list = await notes_cursor.to_list(length=None)
    
    context_parts = []
    context_parts.append(f"Tutorial: {tutorial.get('title', 'Unknown')}")
    url = tutorial.get('url', 'Unknown')
    context_parts.append(f"Link: {url}")
    
    # 3a. Add Transcript context if available
    transcript = tutorial.get('transcript')
    if transcript and current_timestamp is not None:
        start_window = max(0, (current_timestamp - 600) * 1000)
        end_window = (current_timestamp + 600) * 1000
        
        relevant_segments = [
            seg for seg in transcript 
            if (seg.get('offset', 0) >= start_window and seg.get('offset', 0) <= end_window)
        ]
        
        if relevant_segments:
            context_parts.append("\nVideo Transcript (near current timestamp):")
            transcript_text = " ".join([seg.get('text', '') for seg in relevant_segments])
            context_parts.append(transcript_text)
            
    if notes_list:
        context_parts.append("\nNotes from the tutorial:")
        for note in notes_list:
            note_content = note.get('note_content')
            if note_content:
                context_parts.append(f"- {note_content}")
                
    context_message = "\n".join(context_parts)
    system_instruction = f"{TUTORIAL_AI_COMPANION_PROMPT}\n\nContext for this conversation:\n{context_message}"
    
    # 4. Build Messages
    messages = []
    for chat in recent_chats_list:
        messages.append({"role": "user", "content": chat["user"]})
        messages.append({"role": "assistant", "content": chat["ai"]})
        
    messages.append({"role": "user", "content": message})
    
    print(f"[Chats] Calling LLM orchestrator for chat response")
    # 5. Call LLM
    ai_response = await chat_completion_with_fallback(
        messages=messages,
        system_instruction=system_instruction
    )
    
    print(f"[Chats] LLM response received successfully")
    
    # 6. Save to DB
    chat_doc = {
        "tutorial_id": tutorial_id,
        "user_id": user_id,
        "user": message,
        "ai": ai_response,
        "created_at": get_ist_now()
    }
    
    result = await chats.insert_one(chat_doc)
    chat_doc["id"] = str(result.inserted_id)
    
    return chat_doc

async def get_chat_history(user_id: str, tutorial_id: str, skip: int = 0, limit: int = 50) -> dict:
    print(f"[Chats] Fetching chat history for tutorial {tutorial_id}, user {user_id} (skip={skip}, limit={limit})")
    await verify_tutorial_ownership(user_id, tutorial_id)
    chats = get_chat_collection()
    
    total = await chats.count_documents({"tutorial_id": tutorial_id, "user_id": user_id})
    cursor = chats.find({"tutorial_id": tutorial_id, "user_id": user_id}).sort("created_at", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)
    
    # Return chronologically or keep newest first (standard for pagination)
    formatted = []
    for doc in docs:
        doc["id"] = str(doc["_id"])
        formatted.append(doc)
        
    return {
        "meta": {
            "total": total,
            "skip": skip,
            "limit": limit
        },
        "data": formatted
    }
