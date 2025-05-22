from fastapi import APIRouter
from controllers.chats_controller import list_chat_threads_controller
from request_types.chats import ListChatThreadsRequest
from response_types.chats import ListChatThreadsResponse

router = APIRouter()


@router.post("/list-chat-threads", response_model=ListChatThreadsResponse)
def list_chat_threads(data: ListChatThreadsRequest):
    return list_chat_threads_controller(data)
