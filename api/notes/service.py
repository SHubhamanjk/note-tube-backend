from fastapi import HTTPException, status, BackgroundTasks
from bson import ObjectId
from core.database import get_note_collection, get_tutorial_collection, get_group_collection, get_subgroup_collection
from core.utils import get_ist_now
from api.notes import schemas
from api.notes.pdf_generator import generate_notes_pdf_bytes
from api.auth.service import increment_user_counters
from typing import List, Optional

async def verify_tutorial_ownership(user_id: str, tutorial_id: str):
    tutorials = get_tutorial_collection()
    try:
        tut_obj_id = ObjectId(tutorial_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid tutorial ID")
        
    tutorial = await tutorials.find_one({"_id": tut_obj_id, "user_id": user_id})
    if not tutorial:
        raise HTTPException(status_code=404, detail="Tutorial not found or you don't have permission.")
    return tutorial

async def cascade_counter(tutorial, inc_val: int = 1):
    tutorials = get_tutorial_collection()
    groups = get_group_collection()
    subgroups = get_subgroup_collection()
    
    # Update tutorial counter
    await tutorials.update_one(
        {"_id": tutorial["_id"]},
        {"$inc": {"number_of_notes": inc_val}, "$set": {"updated_at": get_ist_now()}}
    )
    
    # Update group counter
    if tutorial.get("group_id"):
        await groups.update_one(
            {"_id": ObjectId(tutorial["group_id"])},
            {"$inc": {"number_of_notes": inc_val}, "$set": {"last_updated": get_ist_now()}}
        )
        
    # Update subgroup counter
    if tutorial.get("subgroup_id"):
        await subgroups.update_one(
            {"_id": ObjectId(tutorial["subgroup_id"])},
            {"$inc": {"number_of_notes": inc_val}, "$set": {"last_updated": get_ist_now()}}
        )

async def create_note(
    user_id: str, 
    tutorial_id: str, 
    note_content: Optional[str], 
    media_urls: List[str],
    timestamp: Optional[str],
    background_tasks: BackgroundTasks
):
    tutorial = await verify_tutorial_ownership(user_id, tutorial_id)
    notes = get_note_collection()
    
    note_dict = {
        "user_id": user_id,
        "tutorial_id": tutorial_id,
        "note_content": note_content,
        "media": media_urls,
        "timestamp": timestamp,
        "created_at": get_ist_now(),
        "updated_at": get_ist_now()
    }
    
    result = await notes.insert_one(note_dict)
    note_dict["id"] = str(result.inserted_id)
    
    # Cascade the counter up the chain in background
    background_tasks.add_task(cascade_counter, tutorial, 1)
    
    # Increment user's notes count
    background_tasks.add_task(increment_user_counters, user_id, "number_of_notes", 1)
    
    return note_dict

async def update_note(
    user_id: str, 
    note_id: str, 
    note_content: Optional[str] = None,
    media_to_keep: List[str] = [],
    new_media_urls: List[str] = []
):
    notes = get_note_collection()
    try:
        obj_id = ObjectId(note_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid note ID")
        
    note = await notes.find_one({"_id": obj_id, "user_id": user_id})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found or permission denied.")
        
    update_data = {"updated_at": get_ist_now()}
    if note_content is not None:
        update_data["note_content"] = note_content
        
    # Merge media: existing to keep + newly uploaded
    final_media = media_to_keep + new_media_urls
    update_data["media"] = final_media
        
    await notes.update_one({"_id": obj_id}, {"$set": update_data})
    return {"message": "Note updated successfully"}

async def delete_note(user_id: str, note_id: str, background_tasks: BackgroundTasks):
    print(f"[Notes] Deleting note {note_id} for user {user_id}")
    notes = get_note_collection()
    try:
        obj_id = ObjectId(note_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid note ID")
        
    note = await notes.find_one({"_id": obj_id, "user_id": user_id})
    if not note:
        raise HTTPException(status_code=404, detail="Note not found or permission denied.")
        
    tutorial = await verify_tutorial_ownership(user_id, note["tutorial_id"])
    
    await notes.delete_one({"_id": obj_id})
    
    # Cascade the decrement in background
    background_tasks.add_task(cascade_counter, tutorial, -1)
    
    # Decrement user's notes count
    background_tasks.add_task(increment_user_counters, user_id, "number_of_notes", -1)
    
    return {"message": "Note deleted successfully"}

async def get_notes_by_tutorial(user_id: str, tutorial_id: str, skip: int = 0, limit: int = 10):
    print(f"[Notes] Fetching notes for tutorial {tutorial_id}, user {user_id} (skip={skip}, limit={limit})")
    await verify_tutorial_ownership(user_id, tutorial_id)
    notes = get_note_collection()
    
    total = await notes.count_documents({"tutorial_id": tutorial_id})
    cursor = notes.find({"tutorial_id": tutorial_id}).sort("created_at", -1).skip(skip).limit(limit)
    note_docs = await cursor.to_list(length=limit)
    
    data = []
    for n in note_docs:
        n["id"] = str(n["_id"])
        data.append(n)
        
    return {
        "meta": {"total": total, "skip": skip, "limit": limit},
        "data": data
    }

async def download_notes_pdf(user_id: str, tutorial_id: str) -> dict:
    print(f"[Notes] Generating PDF for tutorial {tutorial_id}, user {user_id}")
    tutorial = await verify_tutorial_ownership(user_id, tutorial_id)
    notes_coll = get_note_collection()
    
    # Fetch all notes sorted chronologically (oldest to newest)
    cursor = notes_coll.find({"tutorial_id": tutorial_id}).sort("created_at", 1)
    note_docs = await cursor.to_list(length=None)
    
    # Format notes list for PDF generator
    pdf_notes = []
    for n in note_docs:
        pdf_notes.append({
            "timestamp": n.get("timestamp", "0:00"),
            "note_content": n.get("note_content", ""),
            "media_urls": n.get("media", [])
        })
        
    pdf_bytes = generate_notes_pdf_bytes(tutorial.get("title", "Tutorial Notes"), pdf_notes)
    
    # Sanitize title for filename
    safe_title = "".join([c for c in tutorial.get("title", "NoteTube") if c.isalpha() or c.isdigit() or c==' ']).rstrip()
    
    return pdf_bytes, safe_title
