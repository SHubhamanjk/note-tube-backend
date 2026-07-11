from fastapi import APIRouter, status
from api.auth import schemas, service

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(user_in: schemas.UserCreate):
    return await service.create_user(user_in)

@router.post("/login/initiate", status_code=status.HTTP_200_OK)
async def login_initiate(login_in: schemas.LoginInitiate):
    return await service.initiate_login(login_in)

@router.post("/login/confirm", response_model=schemas.TokenResponse, status_code=status.HTTP_200_OK)
async def login_confirm(confirm_in: schemas.LoginConfirm):
    return await service.confirm_login(confirm_in)

@router.post("/forgot-password/initiate", status_code=status.HTTP_200_OK)
async def forgot_password_initiate(forgot_in: schemas.ForgotPasswordInitiate):
    return await service.initiate_forgot_password(forgot_in)

@router.post("/forgot-password/confirm", status_code=status.HTTP_200_OK)
async def forgot_password_confirm(confirm_in: schemas.ForgotPasswordConfirm):
    return await service.confirm_forgot_password(confirm_in)

@router.post("/refresh", status_code=status.HTTP_200_OK)
async def refresh_token(refresh_in: schemas.TokenRefresh):
    return await service.refresh_access_token(refresh_in)

from core.dependencies import get_current_user
from fastapi import Depends

@router.get("/me", response_model=schemas.MeResponse, status_code=status.HTTP_200_OK)
async def get_me(current_user: dict = Depends(get_current_user)):
    return await service.get_me(current_user)
