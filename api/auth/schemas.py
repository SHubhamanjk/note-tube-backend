from pydantic import BaseModel, EmailStr, Field, field_validator

class EmailBase(BaseModel):
    email: EmailStr

    @field_validator('email', mode='before')
    @classmethod
    def lowercase_email(cls, v: str) -> str:
        if isinstance(v, str):
            return v.lower()
        return v

import re

class UserCreate(EmailBase):
    name: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=7)

    @field_validator('password')
    @classmethod
    def validate_strong_password(cls, v: str) -> str:
        if not re.search(r'[a-zA-Z]', v):
            raise ValueError('Password must contain at least one letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number')
        if not re.search(r'[^a-zA-Z0-9]', v):
            raise ValueError('Password must contain at least one special character')
        return v

class LoginInitiate(EmailBase):
    password: str

class LoginConfirm(EmailBase):
    otp: str = Field(..., min_length=6, max_length=6)

class ForgotPasswordInitiate(EmailBase):
    pass

class ForgotPasswordConfirm(EmailBase):
    otp: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=7)

    @field_validator('new_password')
    @classmethod
    def validate_strong_password(cls, v: str) -> str:
        if not re.search(r'[a-zA-Z]', v):
            raise ValueError('Password must contain at least one letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number')
        if not re.search(r'[^a-zA-Z0-9]', v):
            raise ValueError('Password must contain at least one special character')
        return v

class TokenRefresh(BaseModel):
    refresh_token: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict

class MeResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict
    stats: dict
