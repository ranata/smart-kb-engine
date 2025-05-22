from fastapi import HTTPException, status
from services.chats_service import list_chat_threads
from request_types.chats import ListChatThreadsRequest


def list_chat_threads_controller(request: ListChatThreadsRequest):
    data = list_chat_threads(request)
    if data["error"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=data["error"]
        )
    return {
        "data": data["data"],
        "status": "success",
    }
