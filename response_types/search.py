from pydantic import BaseModel
from typing import Optional


class SearchResultResponse(BaseModel):
    data: Optional[str] = None
    conversation_id: Optional[str] = None
    status: Optional[str] = None
    detail: Optional[str] = None
