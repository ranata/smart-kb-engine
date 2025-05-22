from fastapi import APIRouter
from controllers.search_controller import search_knowledge_base_controller
from request_types.search import SearchKnowledgeBaseRequest
from response_types.search import SearchResultResponse

router = APIRouter()


@router.post("/search-knowledge-base", response_model=SearchResultResponse)
def search_knowledge_base_(data: SearchKnowledgeBaseRequest):
    return search_knowledge_base_controller(data)
