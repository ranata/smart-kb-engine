from pydantic import field_validator, create_model, model_validator
from request_types.all_fields import (
    add_topic_fields,
    edit_topic_fields,
    get_topic_fields,
)
from typing import Type


# Add topic request
AddTopicRequestModel: Type = create_model("AddTopicRequest", **add_topic_fields)


class AddTopicRequest(AddTopicRequestModel):
    @model_validator(mode="before")
    @classmethod
    def check_required_fields(cls, values):
        required_fields = ["title", "description", "level", "created_by"]
        for field in required_fields:
            if field not in values or values[field] in [None, ""]:
                raise ValueError(
                    f"{field.replace('_', ' ').title()} is required and cannot be empty"
                )
        return values

    @field_validator("title")
    @classmethod
    def validate_title(cls, value):
        if not value or not value.strip():
            raise ValueError("Title is required and cannot be empty")
        return value

    @field_validator("description")
    @classmethod
    def validate_description(cls, value):
        if not value or not value.strip():
            raise ValueError("Description is required and cannot be empty")
        return value

    @field_validator("level")
    @classmethod
    def validate_level(cls, value):
        if not value or not value.strip():
            raise ValueError("Level is required and cannot be empty")
        return value

    @field_validator("created_by")
    @classmethod
    def validate_created_by(cls, value):
        if not value or not value.strip():
            raise ValueError("Creator id is required and cannot be empty")
        return value


AddTopicRequest.__validators__ = {
    "validate_title": AddTopicRequest.validate_title,
    "validate_description": AddTopicRequest.validate_description,
    "validate_level": AddTopicRequest.validate_level,
    "validate_created_by": AddTopicRequest.validate_created_by,
}

# Edit topic request
EditTopicRequestModel: Type = create_model("EditTopicRequest", **edit_topic_fields)


class EditTopicRequest(EditTopicRequestModel):
    @model_validator(mode="before")
    @classmethod
    def check_required_fields(cls, values):
        required_fields = ["id", "title", "description", "level", "updated_by"]
        for field in required_fields:
            if field not in values or values[field] in [None, ""]:
                raise ValueError(
                    f"{field.replace('_', ' ').title()} is required and cannot be empty"
                )
        return values

    @field_validator("id")
    @classmethod
    def validate_id(cls, value):
        if not value or not value.strip():
            raise ValueError("Topic id is required and cannot be empty")
        return value

    @field_validator("title")
    @classmethod
    def validate_title(cls, value):
        if not value or not value.strip():
            raise ValueError("Title is required and cannot be empty")
        return value

    @field_validator("description")
    @classmethod
    def validate_description(cls, value):
        if not value or not value.strip():
            raise ValueError("Description is required and cannot be empty")
        return value

    @field_validator("level")
    @classmethod
    def validate_level(cls, value):
        if not value or not value.strip():
            raise ValueError("Level is required and cannot be empty")
        return value

    @field_validator("updated_by")
    @classmethod
    def validate_updated_by(cls, value):
        if not value or not value.strip():
            raise ValueError("Modifier id is required and cannot be empty")
        return value


EditTopicRequest.__validators__ = {
    "validate_id": EditTopicRequest.validate_id,
    "validate_title": EditTopicRequest.validate_title,
    "validate_description": EditTopicRequest.validate_description,
    "validate_level": EditTopicRequest.validate_level,
    "validate_updated_by": EditTopicRequest.validate_updated_by,
}

# Load all topic request
GetTopicRequestModel: Type = create_model("GetTopicRequest", **get_topic_fields)


class GetTopicRequest(GetTopicRequestModel):
    pass
