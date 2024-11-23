from pydantic import BaseModel, constr
from datetime import datetime
from typing import Optional, List
from models import TeamRole, InvitationStatus

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
        from_attributes = True

class UserBase(BaseModel):
    email: Optional[str] = None
    name: Optional[str] = None
    nickname: Optional[str] = None
    country_code: Optional[str] = None
    phone_number: Optional[str] = None

    class Config:
        from_attributes = True

class UserCreate(UserBase):
    password: str

class UserResponse(BaseModel):
    id: int
    email: Optional[str] = None
    name: Optional[str] = None
    nickname: Optional[str] = None
    country_code: Optional[str] = None
    phone_number: Optional[str] = None
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

class TeamBase(BaseModel):
    name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True

class TeamCreate(TeamBase):
    pass

class TeamMemberBase(BaseModel):
    user_id: int
    role: constr(pattern='^(owner|member)$') = TeamRole.MEMBER.value

    class Config:
        from_attributes = True

class TeamMemberCreate(TeamMemberBase):
    pass

class ContactInvite(BaseModel):
    email: Optional[str] = None
    phone_number: Optional[str] = None
    country_code: Optional[str] = None
    team_id: Optional[int] = None

class TeamMemberInvite(BaseModel):
    contacts: List[ContactInvite]

class TeamMemberResponse(TeamMemberBase):
    id: int
    team_id: int
    invitation_status: constr(pattern='^(pending|accepted|declined)$')
    invited_by_id: Optional[int]
    invited_at: datetime
    created_at: datetime
    updated_at: Optional[datetime] = None
    user: UserResponse

    class Config:
        from_attributes = True

class InvitationResponse(BaseModel):
    members: List[TeamMemberResponse]
    errors: Optional[List[str]] = None

    class Config:
        from_attributes = True

class TeamResponse(TeamBase):
    id: int
    owner_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    owner: UserResponse
    members: List[TeamMemberResponse]

    class Config:
        from_attributes = True

class TeamInvitationInfo(BaseModel):
    id: int
    team_id: int
    team_name: str
    invited_by_name: Optional[str] = None
    invited_by_email: Optional[str] = None
    invited_at: datetime

    class Config:
        from_attributes = True

class RegistrationResponse(BaseModel):
    id: int
    email: Optional[str] = None
    name: Optional[str] = None
    nickname: Optional[str] = None
    country_code: Optional[str] = None
    phone_number: Optional[str] = None
    created_at: datetime
    pending_invitations: List[TeamInvitationInfo] = []

    class Config:
        from_attributes = True
