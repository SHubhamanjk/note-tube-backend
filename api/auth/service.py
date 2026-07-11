import random
import string
from fastapi import HTTPException, status
from core.database import get_user_collection, get_otp_collection
from core.security import get_password_hash, verify_password, create_access_token, create_refresh_token, decode_token
from core.utils import send_otp_email, get_ist_now
from core.config import settings
from api.auth import schemas
from datetime import datetime

def generate_otp(length: int = 6) -> str:
    return ''.join(random.choices(string.digits, k=length))

async def create_user(user_in: schemas.UserCreate):
    users = get_user_collection()
    existing_user = await users.find_one({"email": user_in.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    user_dict = user_in.model_dump()
    user_dict["password"] = get_password_hash(user_dict["password"])
    user_dict["created_at"] = get_ist_now()
    user_dict["updated_at"] = get_ist_now()
    user_dict["number_of_tutorials"] = 0
    user_dict["number_of_groups"] = 0
    user_dict["number_of_notes"] = 0

    result = await users.insert_one(user_dict)
    return {"id": str(result.inserted_id), "name": user_in.name, "email": user_in.email}

async def initiate_login(login_in: schemas.LoginInitiate):
    users = get_user_collection()
    user = await users.find_one({"email": login_in.email})
    
    if not user or not verify_password(login_in.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    otp = generate_otp()
    otps = get_otp_collection()
    
    # Store OTP (createdAt field is used by TTL index for automatic expiry in 2 mins)
    await otps.update_one(
        {"email": login_in.email},
        {"$set": {"otp": otp, "createdAt": get_ist_now(), "context": "login"}},
        upsert=True
    )
    
    # Send email asynchronously (background task in real prod, but awaiting here for simplicity)
    email_sent = await send_otp_email(login_in.email, otp, context="login")
    if not email_sent:
        raise HTTPException(status_code=500, detail="Failed to send OTP email")
        
    return {"message": "OTP sent to email successfully"}

async def confirm_login(confirm_in: schemas.LoginConfirm):
    otps = get_otp_collection()
    otp_record = await otps.find_one({"email": confirm_in.email, "context": "login"})
    
    if not otp_record or otp_record["otp"] != confirm_in.otp:
        raise HTTPException(status_code=401, detail="Invalid or expired OTP")
    
    # Clean up OTP
    await otps.delete_one({"_id": otp_record["_id"]})
    
    users = get_user_collection()
    user = await users.find_one({"email": confirm_in.email})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user_meta = {"id": str(user["_id"]), "name": user["name"], "email": user["email"]}
    access_token = create_access_token({"sub": user["email"]})
    refresh_token = create_refresh_token({"sub": user["email"]})
    
    return schemas.TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=user_meta
    )

async def initiate_forgot_password(forgot_in: schemas.ForgotPasswordInitiate):
    users = get_user_collection()
    user = await users.find_one({"email": forgot_in.email})
    
    if not user:
        # Don't reveal if user exists or not for security
        return {"message": "If the email is registered, an OTP has been sent."}
        
    otp = generate_otp()
    otps = get_otp_collection()
    
    await otps.update_one(
        {"email": forgot_in.email},
        {"$set": {"otp": otp, "createdAt": get_ist_now(), "context": "forgot_password"}},
        upsert=True
    )
    
    await send_otp_email(forgot_in.email, otp, context="forgot_password")
    return {"message": "If the email is registered, an OTP has been sent."}

async def confirm_forgot_password(confirm_in: schemas.ForgotPasswordConfirm):
    otps = get_otp_collection()
    otp_record = await otps.find_one({"email": confirm_in.email, "context": "forgot_password"})
    
    if not otp_record or otp_record["otp"] != confirm_in.otp:
        raise HTTPException(status_code=401, detail="Invalid or expired OTP")
        
    # Clean up OTP
    await otps.delete_one({"_id": otp_record["_id"]})
    
    users = get_user_collection()
    new_hashed_password = get_password_hash(confirm_in.new_password)
    
    result = await users.update_one(
        {"email": confirm_in.email},
        {"$set": {
            "password": new_hashed_password,
            "updated_at": get_ist_now()
        }}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
        
    return {"message": "Password reset successfully"}

async def refresh_access_token(refresh_in: schemas.TokenRefresh):
    try:
        payload = decode_token(refresh_in.refresh_token, settings.JWT_REFRESH_SECRET)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
            
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token payload")
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid token")
        
    users = get_user_collection()
    user = await users.find_one({"email": email})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    access_token = create_access_token({"sub": email})
    return {"access_token": access_token, "token_type": "bearer"}

async def get_me(current_user: dict):
    user_meta = {
        "id": str(current_user["_id"]),
        "name": current_user.get("name"),
        "email": current_user.get("email")
    }
    
    stats = {
        "number_of_tutorials": current_user.get("number_of_tutorials", 0),
        "number_of_groups": current_user.get("number_of_groups", 0),
        "number_of_notes": current_user.get("number_of_notes", 0)
    }
    
    access_token = create_access_token({"sub": current_user["email"]})
    refresh_token = create_refresh_token({"sub": current_user["email"]})
    
    return schemas.MeResponse(
        user=user_meta,
        stats=stats,
        access_token=access_token,
        refresh_token=refresh_token
    )

async def increment_user_counters(user_id: str, field: str, inc_val: int = 1):
    users = get_user_collection()
    from bson import ObjectId
    try:
        await users.update_one(
            {"_id": ObjectId(user_id)},
            {"$inc": {field: inc_val}, "$set": {"updated_at": get_ist_now()}}
        )
    except Exception as e:
        print(f"Failed to increment user counter {field} for user {user_id}: {e}")
