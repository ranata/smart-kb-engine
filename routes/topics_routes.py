from fastapi import APIRouter
from controllers.topics_controller import (
    create_topics_controller,
    edit_topics_controller,
    get_topics_controller,
    delete_topic_controller,
    view_topic_controller,
)
from request_types.topics import AddTopicRequest, EditTopicRequest, GetTopicRequest
from response_types.topics import (
    CreateTopicResponse,
    EditTopicResponse,
    GetTopicResponse,
    DeleteTopicResponse,
    ViewTopicResponse,
)


router = APIRouter()


@router.post("/create-topics", response_model=CreateTopicResponse)
def create_topics(data: AddTopicRequest):
    return create_topics_controller(data)


@router.post("/edit-topics", response_model=EditTopicResponse)
def edit_topics(data: EditTopicRequest):
    return edit_topics_controller(data)


@router.post("/get-topics", response_model=GetTopicResponse)
def get_topics(data: GetTopicRequest):
    return get_topics_controller(data)


@router.get("/view-topics/{id}", response_model=ViewTopicResponse)
def view_topics(id: str):
    return view_topic_controller(id)


@router.delete("/delete-topic/{id}", response_model=DeleteTopicResponse)
def delete_topic(id: str):
    return delete_topic_controller(id)
