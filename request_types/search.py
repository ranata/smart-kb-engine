from pydantic import field_validator, create_model, model_validator
from request_types.all_fields import search_knowledge_base_fields

from typing import Type

# Search knowledge base request
SearchKnowledgeBaseRequestModel: Type = create_model(
    "SearchKnowledgeBaseRequest", **search_knowledge_base_fields
)


class SearchKnowledgeBaseRequest(SearchKnowledgeBaseRequestModel):
    @model_validator(mode="before")
    @classmethod
    def check_required_fields(cls, values):
        required_fields = [
            "search_key",
            "username",
        ]
        for field in required_fields:
            if field not in values or values[field] in [None, ""]:
                raise ValueError(
                    f"{field.replace('_', ' ').title()} is required and cannot be empty"
                )
        return values

    @field_validator("search_key")
    @classmethod
    def validate_search_key(cls, value):
        if not value or not value.strip():
            raise ValueError("Search key is required and cannot be empty")
        return value

    @field_validator("username")
    @classmethod
    def validate_username(cls, value):
        if not value or not value.strip():
            raise ValueError("Username is required and cannot be empty")
        return value


SearchKnowledgeBaseRequest.__validators__ = {
    "validate_search_key": SearchKnowledgeBaseRequest.validate_search_key,
    "validate_username": SearchKnowledgeBaseRequest.validate_username,
}
