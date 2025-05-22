from pydantic import BaseModel
from typing import Optional


class DefaultTableCreationResponse(BaseModel):
    data: Optional[str] = None
    status: Optional[str] = None
    detail: Optional[str] = None
