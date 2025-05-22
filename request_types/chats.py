from pydantic import field_validator, create_model, model_validator
from request_types.all_fields import list_chat_threads_fields

from typing import Type

# List chat threads base request
ListChatThreadsBaseRequestModel: Type = create_model(
    "ListChatThreadsRequest", **list_chat_threads_fields
)


class ListChatThreadsRequest(ListChatThreadsBaseRequestModel):
    @model_validator(mode="before")
    @classmethod
    def check_required_fields(cls, values):
        required_fields = ["username"]
        for field in required_fields:
            if field not in values or values[field] in [None, ""]:
                raise ValueError(
                    f"{field.replace('_', ' ').title()} is required and cannot be empty"
                )
        return values

    @field_validator("username")
    @classmethod
    def validate_username(cls, value):
        if not value or not value.strip():
            raise ValueError("Username is required and cannot be empty")
        return value


ListChatThreadsRequest.__validators__ = {
    "validate_username": ListChatThreadsRequest.validate_username,
}
