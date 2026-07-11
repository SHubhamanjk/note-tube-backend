from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from core.security import decode_token
from core.database import get_user_collection
from core.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login/confirm")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = decode_token(token, settings.JWT_SECRET)
    if not payload:
        raise credentials_exception
        
    email: str = payload.get("sub")
    if email is None:
        raise credentials_exception
        
    users = get_user_collection()
    user = await users.find_one({"email": email})
    
    if user is None:
        raise credentials_exception
        
    return user
