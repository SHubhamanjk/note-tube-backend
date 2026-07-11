from fastapi import HTTPException
from bson import ObjectId
from core.database import get_chat_collection, get_tutorial_collection, get_note_collection
from core.utils import get_ist_now
from core.llm import chat_completion_with_fallback
from core.prompts import TUTORIAL_AI_COMPANION_PROMPT
from typing import List, Dict, Any
import re
from youtube_transcript_api import YouTubeTranscriptApi

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

def get_youtube_video_id(url: str) -> str:
    """Extract YouTube video ID from URL."""
    if not url:
        return None
    patterns = [
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([^&]+)',
        r'(?:https?:\/\/)?(?:www\.)?youtu\.be\/([^?]+)',
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/embed\/([^?]+)'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def fetch_transcript(video_id: str) -> list:
    """Fetch raw structured transcript using youtube-transcript-api."""
    print(f"[Chats] Fetching transcript for video {video_id}")
    try:
        # Comprehensive list of common language codes to try (fallback cascade)
        langs = ('en', 'hi', 'es', 'fr', 'de', 'ja', 'ko', 'ru', 'pt', 'it', 'zh-Hans', 'zh-Hant', 'ar', 'te', 'ta', 'mr', 'bn', 'gu', 'ur', 'ml', 'kn', 'en-US', 'en-GB')
        
        raw_transcript = None
        
        # In modern versions, it's a class method on YouTubeTranscriptApi
        if hasattr(YouTubeTranscriptApi, 'get_transcript'):
            raw_transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=langs)
        else:
            # In some versions, it requires instantiation
            api_instance = YouTubeTranscriptApi() if callable(YouTubeTranscriptApi) else YouTubeTranscriptApi
            if hasattr(api_instance, 'get_transcript'):
                raw_transcript = api_instance.get_transcript(video_id, languages=langs)
            # Fallback to fetch (often used in very old or alternative versions)
            elif hasattr(api_instance, 'fetch'):
                try:
                    raw_transcript = api_instance.fetch(video_id, languages=langs)
                except TypeError:
                    # If fetch doesn't accept languages
                    raw_transcript = api_instance.fetch(video_id)
                    
        if not raw_transcript:
            return None
            
        # Normalize the result into a list of dicts
        normalized = []
        # If it's a FetchedTranscript object (has snippets attribute)
        if hasattr(raw_transcript, 'snippets'):
            for s in raw_transcript.snippets:
                normalized.append({
                    'text': getattr(s, 'text', ''),
                    'start': getattr(s, 'start', 0.0),
                    'duration': getattr(s, 'duration', 0.0)
                })
            return normalized
            
        # If it's already a list, ensure it's a list of dicts
        if isinstance(raw_transcript, list):
            for item in raw_transcript:
                if hasattr(item, 'text'):
                    normalized.append({
                        'text': getattr(item, 'text', ''),
                        'start': getattr(item, 'start', 0.0),
                        'duration': getattr(item, 'duration', 0.0)
                    })
                elif isinstance(item, dict):
                    normalized.append(item)
            return normalized
            
        return raw_transcript
    except Exception as e:
        print(f"Transcript fetch error: {e}")
        return None

def extract_transcript_window(transcript_list: list, current_timestamp: float, window_minutes: int = 10) -> str:
    """Extract transcript text from a time window around the current timestamp."""
    if not transcript_list:
        return ""
        
    if current_timestamp is None:
        # If no timestamp, return the first 15000 chars as fallback
        full_text = " ".join([t['text'] for t in transcript_list])
        return full_text[:15000] + "... (truncated)"
        
    window_seconds = window_minutes * 60
    start_time = max(0, current_timestamp - window_seconds)
    end_time = current_timestamp + window_seconds
    
    window_text = []
    for t in transcript_list:
        # If the transcript segment falls within our window
        if t['start'] + t.get('duration', 0) >= start_time and t['start'] <= end_time:
            window_text.append(t['text'])
            
    return " ".join(window_text)

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
    
    # 3. Build Context
    context_parts = []
    context_parts.append(f"Tutorial: {tutorial.get('title', 'Unknown')}")
    url = tutorial.get('url', 'Unknown')
    context_parts.append(f"Link: {url}")
    
    # Try fetching transcript from DB first (cache)
    transcript = tutorial.get('transcript')
    
    if not transcript:
        # Not in DB, fetch via network
        video_id = get_youtube_video_id(url)
        if video_id:
            transcript = fetch_transcript(video_id)
            if transcript:
                # Save to database to cache it for all future chats!
                tutorials = get_tutorial_collection()
                await tutorials.update_one(
                    {"_id": tutorial["_id"]},
                    {"$set": {"transcript": transcript}}
                )
                
                
    if transcript:
        # Extract only the relevant window if timestamp is provided
        windowed_text = extract_transcript_window(transcript, current_timestamp)
        if windowed_text:
            context_parts.append(f"\nVideo Transcript Context (around {current_timestamp if current_timestamp else 'start'}s):\n{windowed_text}\n")
            
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
