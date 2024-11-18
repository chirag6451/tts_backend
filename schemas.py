from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    audio_path: Optional[str] = None

    class Config:
        from_attributes = True

class TaskCreate(TaskBase):
    pass

class TaskResponse(BaseModel):
    id: int
    title: str
    description: str
    status: str
    audio_path: Optional[str] = None
    audio_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    user_id: int

    class Config:
        orm_mode = True

class UserBase(BaseModel):
    email: str

    class Config:
        from_attributes = True

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: int

class AudioUploadResponse(BaseModel):
    success: bool
    message: str
    task: dict

    class Config:
        from_attributes = True
