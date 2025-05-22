from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ScrapeData(BaseModel):
    url_or_html: Optional[str] = None
    s3_location: Optional[str] = None


class ScrapeContentResponse(BaseModel):
    data: ScrapeData
    status: Optional[str] = None
    detail: Optional[str] = None


class CreateContentResponse(BaseModel):
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


class ContentData(BaseModel):
    id: int
    source: str
    title: str
    description: str
    source_info: str
    source_data: str
    status: str
    version: str
    topic_ids: List[int]
    tags: str
    created_by: str
    stored_in_kb: Optional[str]
    is_deleted: bool
    created_at: datetime
    s3_source_url: Optional[str] = None
    updated_at: Optional[datetime] = None
    review_date: Optional[datetime] = None
    approved_time: Optional[datetime] = None
    rejected_time: Optional[datetime] = None
    create_user_data: Optional[CognitoUserDetailResponse] = None
    update_user_data: Optional[CognitoUserDetailResponse] = None


class GetContentResponse(BaseModel):
    data: Optional[List[ContentData]] = []
    status: Optional[str] = None
    detail: Optional[str] = None


class ViewContentResponse(BaseModel):
    data: Optional[ContentData] = None
    status: Optional[str] = None
    detail: Optional[str] = None


class EditContentResponse(BaseModel):
    data: Optional[str] = None
    status: Optional[str] = None
    detail: Optional[str] = None


class DeleteContentResponse(BaseModel):
    data: Optional[str] = None
    status: Optional[str] = None
    detail: Optional[str] = None


class ParseContentResponse(BaseModel):
    data: Optional[str] = None
    status: Optional[str] = None
    detail: Optional[str] = None
