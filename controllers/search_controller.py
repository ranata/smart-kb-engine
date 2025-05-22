from fastapi import HTTPException, status
from services.search_service import search_knowledge_base
from request_types.search import SearchKnowledgeBaseRequest


def search_knowledge_base_controller(request: SearchKnowledgeBaseRequest):
    data = search_knowledge_base(request)
    if data["error"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=data["error"]
        )
    return {
        "data": data["data"],
        "conversation_id": data["conversation_id"],
        "status": "success",
    }
