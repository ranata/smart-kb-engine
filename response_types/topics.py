from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class CreateTopicResponse(BaseModel):
    data: Optional[str] = None
    status: Optional[str] = None
    detail: Optional[str] = None


class EditTopicResponse(BaseModel):
    data: Optional[str] = None
    status: Optional[str] = None
    detail: Optional[str] = None


class TopicData(BaseModel):
    id: int
    title: str
    description: str
    collection_name: str
    level: str
    tenant: str
    facility: str
    created_by: str
    is_deleted: bool
    created_at: datetime
    updated_at: datetime


class GetTopicResponse(BaseModel):
    data: List[TopicData]
    status: str


class DeleteTopicResponse(BaseModel):
    data: Optional[str] = None
    status: Optional[str] = None
    detail: Optional[str] = None


class CognitoUserDetailResponse(BaseModel):
    message: Optional[str] = None
    sub: Optional[str] = None
    timezone: Optional[str] = None
    email_verified: Optional[str] = None
    temperature_unit: Optional[str] = None
    lastLogin: Optional[str] = None
    notification: Optional[str] = None
    phone_number_verified: Optional[str] = None
    middle_name: Optional[str] = None
    email_message: Optional[str] = None
    picture: Optional[str] = None
    tenantId: Optional[str] = None
    phone: Optional[str] = None
    name: Optional[str] = None
    phone_number: Optional[str] = None
    profile_updated: Optional[str] = None
    email: Optional[str] = None


class ViewTopicData(BaseModel):
    id: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    level: Optional[str] = None
    created_by: Optional[str] = None
    is_deleted: Optional[bool] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    tenant: Optional[str] = None
    facility: Optional[str] = None
    updated_by: Optional[str] = None
    create_user_data: Optional[CognitoUserDetailResponse] = None
    update_user_data: Optional[CognitoUserDetailResponse] = None


class ViewTopicResponse(BaseModel):
    data: Optional[ViewTopicData] = None
    status: Optional[str] = None
    detail: Optional[str] = None
