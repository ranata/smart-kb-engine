from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ConversationData(BaseModel):
    id: int
    name: str
    username: str
    created_at: datetime
    updated_at: datetime


class ListChatThreadsResponse(BaseModel):
    data: Optional[List[ConversationData]] = None
    status: Optional[str] = None
    detail: Optional[str] = None
