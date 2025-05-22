from fastapi import HTTPException, status
from services.topics_service import (
    create_topics,
    edit_topics,
    get_topics_list,
    delete_topic,
    view_topic,
)
from request_types.topics import AddTopicRequest, EditTopicRequest, GetTopicRequest


def create_topics_controller(request: AddTopicRequest):
    data = create_topics(request)
    if data["error"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=data["error"]
        )
    return {"data": data["data"], "status": "success"}


def edit_topics_controller(request: EditTopicRequest):
    data = edit_topics(request)
    if data["error"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=data["error"]
        )
    return {"data": data["data"], "status": "success"}


def get_topics_controller(request: GetTopicRequest):
    data = get_topics_list(request)
    if data["error"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=data["error"]
        )
    return {"data": data["data"], "status": "success"}


def view_topic_controller(id: str):
    data = view_topic(id)
    if data["error"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=data["error"]
        )
    return {"data": data["data"], "status": "success"}


def delete_topic_controller(id: str):
    data = delete_topic(id)
    if data["error"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=data["error"]
        )
    return {"data": data["data"], "status": "success"}
