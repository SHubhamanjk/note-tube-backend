from fastapi import HTTPException, status, BackgroundTasks
from pymongo.errors import DuplicateKeyError
from core.database import get_group_collection, get_subgroup_collection
from core.utils import get_ist_now
from api.groups import schemas
from api.auth.service import increment_user_counters

async def create_group(user_id: str, group_in: schemas.GroupCreate, background_tasks: BackgroundTasks) -> dict:
    print(f"[Groups] Creating new group for user {user_id}: {group_in.group_name}")
    groups = get_group_collection()
    
    group_dict = {
        "user_id": user_id,
        "group_name": group_in.group_name,
        "created_at": get_ist_now(),
        "last_updated": get_ist_now(),
        "number_of_tutorials": 0,
        "number_of_notes": 0,
        "number_of_subgroups": 0
    }
    
    try:
        result = await groups.insert_one(group_dict)
        group_dict["id"] = str(result.inserted_id)
        if "_id" in group_dict:
            del group_dict["_id"]
        group_dict["subgroups"] = []
        
        # Increment user's groups count
        background_tasks.add_task(increment_user_counters, user_id, "number_of_groups", 1)
        
        return group_dict
    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A group with this name already exists for this user."
        )

async def get_user_groups(user_id: str, skip: int = 0, limit: int = 10):
    print(f"[Groups] Fetching groups for user {user_id} (skip={skip}, limit={limit})")
    groups_coll = get_group_collection()
    subgroups_coll = get_subgroup_collection()
    
    total = await groups_coll.count_documents({"user_id": user_id})
    cursor = groups_coll.find({"user_id": user_id}).skip(skip).limit(limit)
    groups = await cursor.to_list(length=limit)
    
    data = []
    for g in groups:
        g["id"] = str(g["_id"])
        
        # Fetch all subgroups for this group (no pagination here, or we fetch all)
        # To avoid massive N+1 queries, an aggregation pipeline could be used,
        # but for typical small numbers of subgroups, fetching directly is straightforward.
        sub_cursor = subgroups_coll.find({"group_id": g["id"]})
        subgroups = await sub_cursor.to_list(length=None)
        
        parsed_subgroups = []
        for sg in subgroups:
            sg["id"] = str(sg["_id"])
            parsed_subgroups.append(sg)
            
        g["subgroups"] = parsed_subgroups
        data.append(g)
        
    return {
        "meta": {"total": total, "skip": skip, "limit": limit},
        "data": data
    }

async def get_user_group_names(user_id: str):
    groups_coll = get_group_collection()
    subgroups_coll = get_subgroup_collection()
    
    cursor = groups_coll.find({"user_id": user_id}, {"group_name": 1})
    groups = await cursor.to_list(length=None)
    
    result = []
    for g in groups:
        group_id = str(g["_id"])
        
        # Fetch subgroups for this group
        sub_cursor = subgroups_coll.find({"group_id": group_id}, {"subgroup_name": 1})
        subgroups = await sub_cursor.to_list(length=None)
        
        parsed_subgroups = []
        for sg in subgroups:
            parsed_subgroups.append({
                "id": str(sg["_id"]),
                "subgroup_name": sg["subgroup_name"]
            })
            
        result.append({
            "id": group_id, 
            "group_name": g["group_name"],
            "subgroups": parsed_subgroups
        })
        
    return result

async def create_subgroup(group_id: str, subgroup_in: schemas.SubGroupCreate):
    groups = get_group_collection()
    from bson import ObjectId
    
    parent_group = await groups.find_one({"_id": ObjectId(group_id)})
    if not parent_group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found.")
        
    subgroups = get_subgroup_collection()
    
    subgroup_dict = {
        "group_id": group_id,
        "subgroup_name": subgroup_in.subgroup_name,
        "created_at": get_ist_now(),
        "last_updated": get_ist_now(),
        "number_of_tutorials": 0,
        "number_of_notes": 0
    }
    
    try:
        result = await subgroups.insert_one(subgroup_dict)
        subgroup_dict["id"] = str(result.inserted_id)
        
        await groups.update_one(
            {"_id": ObjectId(group_id)},
            {"$inc": {"number_of_subgroups": 1}, "$set": {"last_updated": get_ist_now()}}
        )
        
        return subgroup_dict
    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A subgroup with this name already exists in this group."
        )

async def get_subgroups_for_group(group_id: str, skip: int = 0, limit: int = 10):
    subgroups_coll = get_subgroup_collection()
    
    total = await subgroups_coll.count_documents({"group_id": group_id})
    cursor = subgroups_coll.find({"group_id": group_id}).skip(skip).limit(limit)
    subgroups = await cursor.to_list(length=limit)
    
    data = []
    for sg in subgroups:
        sg["id"] = str(sg["_id"])
        data.append(sg)
        
    return {
        "meta": {"total": total, "skip": skip, "limit": limit},
        "data": data
    }

async def get_subgroup_names(group_id: str):
    subgroups_coll = get_subgroup_collection()
    cursor = subgroups_coll.find({"group_id": group_id}, {"subgroup_name": 1})
    subgroups = await cursor.to_list(length=None)
    
    result = []
    for sg in subgroups:
        result.append({"id": str(sg["_id"]), "subgroup_name": sg["subgroup_name"]})
        
    return result

async def update_group(user_id: str, group_id: str, group_in: schemas.GroupUpdate):
    groups = get_group_collection()
    from bson import ObjectId
    
    try:
        obj_id = ObjectId(group_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid group ID")
        
    try:
        result = await groups.update_one(
            {"_id": obj_id, "user_id": user_id},
            {"$set": {"group_name": group_in.group_name, "last_updated": get_ist_now()}}
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Group not found or you don't have permission.")
        return {"message": "Group updated successfully"}
    except DuplicateKeyError:
        raise HTTPException(status_code=400, detail="A group with this name already exists.")

async def delete_group(user_id: str, group_id: str, background_tasks: BackgroundTasks):
    groups = get_group_collection()
    subgroups = get_subgroup_collection()
    from bson import ObjectId
    
    try:
        obj_id = ObjectId(group_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid group ID")
        
    result = await groups.delete_one({"_id": obj_id, "user_id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Group not found or you don't have permission.")
        
    # Cascade delete all subgroups under this group
    await subgroups.delete_many({"group_id": group_id})
    
    # Decrement user's groups count
    background_tasks.add_task(increment_user_counters, user_id, "number_of_groups", -1)
    
    return {"message": "Group and its subgroups deleted successfully"}

async def update_subgroup(user_id: str, group_id: str, subgroup_id: str, subgroup_in: schemas.SubGroupUpdate):
    groups = get_group_collection()
    subgroups = get_subgroup_collection()
    from bson import ObjectId
    
    try:
        grp_obj_id = ObjectId(group_id)
        sub_obj_id = ObjectId(subgroup_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid ID")
        
    # Verify user owns the parent group
    parent = await groups.find_one({"_id": grp_obj_id, "user_id": user_id})
    if not parent:
        raise HTTPException(status_code=404, detail="Parent group not found or you don't have permission.")
        
    try:
        result = await subgroups.update_one(
            {"_id": sub_obj_id, "group_id": group_id},
            {"$set": {"subgroup_name": subgroup_in.subgroup_name, "last_updated": get_ist_now()}}
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Subgroup not found.")
            
        # Update parent's last_updated
        await groups.update_one({"_id": grp_obj_id}, {"$set": {"last_updated": get_ist_now()}})
        
        return {"message": "Subgroup updated successfully"}
    except DuplicateKeyError:
        raise HTTPException(status_code=400, detail="A subgroup with this name already exists in this group.")

async def delete_subgroup(user_id: str, group_id: str, subgroup_id: str):
    groups = get_group_collection()
    subgroups = get_subgroup_collection()
    from bson import ObjectId
    
    try:
        grp_obj_id = ObjectId(group_id)
        sub_obj_id = ObjectId(subgroup_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid ID")
        
    # Verify user owns the parent group
    parent = await groups.find_one({"_id": grp_obj_id, "user_id": user_id})
    if not parent:
        raise HTTPException(status_code=404, detail="Parent group not found or you don't have permission.")
        
    result = await subgroups.delete_one({"_id": sub_obj_id, "group_id": group_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Subgroup not found.")
        
    # Decrement parent's subgroup count
    await groups.update_one(
        {"_id": grp_obj_id}, 
        {"$inc": {"number_of_subgroups": -1}, "$set": {"last_updated": get_ist_now()}}
    )
    
    return {"message": "Subgroup deleted successfully"}
