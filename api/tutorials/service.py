from fastapi import HTTPException, status, BackgroundTasks
from bson import ObjectId
from core.database import get_tutorial_collection, get_group_collection, get_subgroup_collection
from core.utils import get_ist_now
from api.tutorials import schemas
from api.auth.service import increment_user_counters

async def verify_group_ownership(user_id: str, group_id: str):
    groups = get_group_collection()
    try:
        grp_obj_id = ObjectId(group_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid group ID")
        
    group = await groups.find_one({"_id": grp_obj_id, "user_id": user_id})
    if not group:
        raise HTTPException(status_code=404, detail="Group not found or you do not have permission.")
    return grp_obj_id

async def verify_subgroup_ownership(user_id: str, group_id: str, subgroup_id: str):
    print(f"[Tutorials] Verifying subgroup {subgroup_id} ownership for user {user_id}")
    await verify_group_ownership(user_id, group_id)
    
    subgroups = get_subgroup_collection()
    try:
        sub_obj_id = ObjectId(subgroup_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid subgroup ID")
        
    subgroup = await subgroups.find_one({"_id": sub_obj_id, "group_id": group_id})
    if not subgroup:
        raise HTTPException(status_code=404, detail="Subgroup not found.")
    return sub_obj_id

async def increment_counters(group_id: str = None, subgroup_id: str = None, inc_val: int = 1):
    if group_id:
        groups = get_group_collection()
        await groups.update_one(
            {"_id": ObjectId(group_id)},
            {"$inc": {"number_of_tutorials": inc_val}, "$set": {"last_updated": get_ist_now()}}
        )
    if subgroup_id:
        subgroups = get_subgroup_collection()
        await subgroups.update_one(
            {"_id": ObjectId(subgroup_id)},
            {"$inc": {"number_of_tutorials": inc_val}, "$set": {"last_updated": get_ist_now()}}
        )

async def create_tutorial(user_id: str, tutorial_in: schemas.TutorialCreate, background_tasks: BackgroundTasks):
    if tutorial_in.group_id == "general":
        tutorial_in.group_id = None
        
    print(f"[Tutorials] Creating tutorial for user {user_id}, group {tutorial_in.group_id}")
    if tutorial_in.group_id and tutorial_in.subgroup_id:
        await verify_subgroup_ownership(user_id, tutorial_in.group_id, tutorial_in.subgroup_id)
    elif tutorial_in.group_id:
        await verify_group_ownership(user_id, tutorial_in.group_id)
        
    tutorials = get_tutorial_collection()
    
    tutorial_dict = {
        "user_id": user_id,
        "url": str(tutorial_in.url),
        "title": tutorial_in.title,
        "created_at": get_ist_now(),
        "updated_at": get_ist_now(),
        "number_of_notes": 0,
        "group_id": tutorial_in.group_id,
        "subgroup_id": tutorial_in.subgroup_id,
        "transcript": [t.model_dump() for t in tutorial_in.transcript] if tutorial_in.transcript else None
    }
    
    result = await tutorials.insert_one(tutorial_dict)
    tutorial_dict["id"] = str(result.inserted_id)
    
    # Increment user's tutorials count
    background_tasks.add_task(increment_user_counters, user_id, "number_of_tutorials", 1)
    
    # Increment group counts in background if assigned
    if tutorial_dict["group_id"]:
        background_tasks.add_task(increment_counters, tutorial_dict["group_id"], tutorial_dict.get("subgroup_id"), 1)
    
    return tutorial_dict

async def delete_tutorial(user_id: str, tutorial_id: str, background_tasks: BackgroundTasks):
    print(f"[Tutorials] Deleting tutorial {tutorial_id} for user {user_id}")
    tutorials = get_tutorial_collection()
    try:
        obj_id = ObjectId(tutorial_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid tutorial ID")
        
    tutorial = await tutorials.find_one({"_id": obj_id, "user_id": user_id})
    if not tutorial:
        raise HTTPException(status_code=404, detail="Tutorial not found or you don't have permission.")
        
    await tutorials.delete_one({"_id": obj_id})
    
    # Decrement user's tutorials count
    background_tasks.add_task(increment_user_counters, user_id, "number_of_tutorials", -1)
    
    # Decrement counters in background
    background_tasks.add_task(increment_counters, tutorial.get("group_id"), tutorial.get("subgroup_id"), -1)
    
    return {"message": "Tutorial deleted successfully"}

async def update_tutorial(user_id: str, tutorial_id: str, tutorial_in: schemas.TutorialUpdate, background_tasks: BackgroundTasks):
    if tutorial_in.group_id == "general":
        tutorial_in.group_id = None
        
    tutorials = get_tutorial_collection()
    try:
        obj_id = ObjectId(tutorial_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid tutorial ID")
        
    tutorial = await tutorials.find_one({"_id": obj_id, "user_id": user_id})
    if not tutorial:
        raise HTTPException(status_code=404, detail="Tutorial not found or you don't have permission.")
        
    old_group = tutorial.get("group_id")
    old_subgroup = tutorial.get("subgroup_id")
    
    new_group = tutorial_in.group_id if tutorial_in.group_id is not None else old_group
    new_subgroup = tutorial_in.subgroup_id if tutorial_in.subgroup_id is not None else old_subgroup
    
    # Validation if group changed
    if tutorial_in.group_id is not None and tutorial_in.group_id != old_group:
        if new_group and new_subgroup:
            await verify_subgroup_ownership(user_id, new_group, new_subgroup)
        elif new_group:
            await verify_group_ownership(user_id, new_group)
    elif tutorial_in.subgroup_id is not None and tutorial_in.subgroup_id != old_subgroup:
        if new_subgroup:
            await verify_subgroup_ownership(user_id, new_group, new_subgroup)
            
    update_data = {"updated_at": get_ist_now()}
    if tutorial_in.title is not None:
        update_data["title"] = tutorial_in.title
    if tutorial_in.group_id is not None:
        update_data["group_id"] = tutorial_in.group_id
    if tutorial_in.subgroup_id is not None:
        update_data["subgroup_id"] = tutorial_in.subgroup_id
        
    await tutorials.update_one({"_id": obj_id}, {"$set": update_data})
    
    # Handle counter shifts in background
    # Decrement old
    if tutorial_in.group_id is not None and tutorial_in.group_id != old_group:
        background_tasks.add_task(increment_counters, old_group, None, -1)
        background_tasks.add_task(increment_counters, new_group, None, 1)
        
    if tutorial_in.subgroup_id is not None and tutorial_in.subgroup_id != old_subgroup:
        background_tasks.add_task(increment_counters, None, old_subgroup, -1)
        background_tasks.add_task(increment_counters, None, new_subgroup, 1)
        
    return {"message": "Tutorial updated successfully"}

async def get_tutorials(user_id: str, skip: int = 0, limit: int = 50, group_id: str = None, subgroup_id: str = None) -> dict:
    print(f"[Tutorials] Fetching tutorials for user {user_id} (skip={skip}, limit={limit})")
    tutorials = get_tutorial_collection()
    
    total = await tutorials.count_documents({"user_id": user_id})
    cursor = tutorials.find({"user_id": user_id}).skip(skip).limit(limit)
    tutorial_docs = await cursor.to_list(length=limit)
    
    data = []
    for t in tutorial_docs:
        t["id"] = str(t["_id"])
        data.append(t)
        
    return {
        "meta": {"total": total, "skip": skip, "limit": limit},
        "data": data
    }

async def get_user_tutorials(user_id: str, skip: int = 0, limit: int = 10):
    tutorials = get_tutorial_collection()
    
    total = await tutorials.count_documents({"user_id": user_id})
    cursor = tutorials.find({"user_id": user_id}).skip(skip).limit(limit)
    tutorial_docs = await cursor.to_list(length=limit)
    
    data = []
    for t in tutorial_docs:
        t["id"] = str(t["_id"])
        data.append(t)
        
    return {
        "meta": {"total": total, "skip": skip, "limit": limit},
        "data": data
    }

async def get_tutorials_by_group(group_id: str, skip: int = 0, limit: int = 10):
    tutorials = get_tutorial_collection()
    
    total = await tutorials.count_documents({"group_id": group_id})
    cursor = tutorials.find({"group_id": group_id}).skip(skip).limit(limit)
    tutorial_docs = await cursor.to_list(length=limit)
    
    data = []
    for t in tutorial_docs:
        t["id"] = str(t["_id"])
        data.append(t)
        
    return {
        "meta": {"total": total, "skip": skip, "limit": limit},
        "data": data
    }

async def get_tutorials_by_subgroup(subgroup_id: str, skip: int = 0, limit: int = 10):
    tutorials = get_tutorial_collection()
    
    total = await tutorials.count_documents({"subgroup_id": subgroup_id})
    cursor = tutorials.find({"subgroup_id": subgroup_id}).skip(skip).limit(limit)
    tutorial_docs = await cursor.to_list(length=limit)
    
    data = []
    for t in tutorial_docs:
        t["id"] = str(t["_id"])
        data.append(t)
        
    return {
        "meta": {"total": total, "skip": skip, "limit": limit},
        "data": data
    }

async def get_tutorial_by_url(user_id: str, url: str):
    tutorials = get_tutorial_collection()
    tutorial = await tutorials.find_one({"user_id": user_id, "url": url})
    if not tutorial:
        raise HTTPException(status_code=404, detail="Tutorial not found")
        
    tutorial["id"] = str(tutorial["_id"])
    return tutorial

async def assign_tutorial_to_group(user_id: str, tutorial_id: str, assign_data: schemas.TutorialAssignGroup, background_tasks: BackgroundTasks):
    if assign_data.group_id == "general":
        assign_data.group_id = None
        
    tutorials = get_tutorial_collection()
    try:
        obj_id = ObjectId(tutorial_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid tutorial ID")
        
    tutorial = await tutorials.find_one({"_id": obj_id, "user_id": user_id})
    if not tutorial:
        raise HTTPException(status_code=404, detail="Tutorial not found or permission denied.")
        
    old_group = tutorial.get("group_id")
    old_subgroup = tutorial.get("subgroup_id")
    
    new_group = assign_data.group_id
    new_subgroup = assign_data.subgroup_id
    
    if new_group and new_subgroup:
        await verify_subgroup_ownership(user_id, new_group, new_subgroup)
    elif new_group:
        await verify_group_ownership(user_id, new_group)
        
    update_data = {
        "updated_at": get_ist_now(),
        "group_id": new_group,
        "subgroup_id": new_subgroup
    }
    
    await tutorials.update_one({"_id": obj_id}, {"$set": update_data})
    
    # Decrement old counts
    if old_group != new_group:
        if old_group:
            background_tasks.add_task(increment_counters, old_group, None, -1)
        if new_group:
            background_tasks.add_task(increment_counters, new_group, None, 1)
            
    if old_subgroup != new_subgroup:
        if old_subgroup:
            background_tasks.add_task(increment_counters, None, old_subgroup, -1)
        if new_subgroup:
            background_tasks.add_task(increment_counters, None, new_subgroup, 1)
            
    tutorial["group_id"] = new_group
    tutorial["subgroup_id"] = new_subgroup
    tutorial["updated_at"] = update_data["updated_at"]
    tutorial["id"] = str(tutorial["_id"])
    if "_id" in tutorial:
        del tutorial["_id"]
    return tutorial
