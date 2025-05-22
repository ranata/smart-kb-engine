from pydantic import field_validator, create_model, model_validator
from request_types.all_fields import (
    content_scrape_fields,
    create_content_fields,
    get_content_fields,
    edit_content_fields,
    parse_content_fields,
)
from config.constants import ALLOWED_EXTENSIONS, CONTENT_STATUS
from fastapi import HTTPException, UploadFile, Form
from typing import Optional, Type


# content scrape request
ScrapeDataRequestModel: Type = create_model(
    "ScrapeDataRequestModel", **content_scrape_fields
)


class ScrapeDataRequest(ScrapeDataRequestModel):
    @model_validator(mode="before")
    @classmethod
    def check_required_fields(cls, values):
        required_fields = [
            "url",
            "type",
            "username",
        ]
        for field in required_fields:
            if field not in values or values[field] in [None, ""]:
                raise ValueError(
                    f"{field.replace('_', ' ').title()} is required and cannot be empty"
                )
        return values

    @field_validator("url")
    @classmethod
    def validate_url(cls, value):
        if not value or not value.strip():
            raise ValueError("Url is required and cannot be empty")
        return value

    @field_validator("type")
    @classmethod
    def validate_type(cls, value):
        if not value or not value.strip():
            raise ValueError("Type is required and cannot be empty")
        if value not in ["LINK", "DRIVE", "DROPBOX"]:
            raise ValueError(
                "Invalid type. Allowed values are: 'LINK', 'DRIVE', 'DROPBOX'."
            )
        return value

    @field_validator("username")
    @classmethod
    def validate_username(cls, value):
        if not value or not value.strip():
            raise ValueError("Username is required and cannot be empty")
        return value


ScrapeDataRequest.__validators__ = {
    "validate_url": ScrapeDataRequest.validate_url,
    "validate_type": ScrapeDataRequest.validate_type,
    "validate_username": ScrapeDataRequest.validate_username,
}


CreateContentRequestModel: Type = create_model(
    "CreateContentRequestModel", **create_content_fields
)


# create content request
class CreateContentRequest(CreateContentRequestModel):
    @model_validator(mode="before")
    @classmethod
    def check_required_fields(cls, values):
        required_fields = [
            "title",
            "description",
            "source_info",
            "tags",
            "level",
            "created_by",
            "topic_ids",
            "username",
        ]
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
        return value.strip()

    @field_validator("description")
    @classmethod
    def validate_description(cls, value):
        if not value or not value.strip():
            raise ValueError("Description is required and cannot be empty")
        return value.strip()

    @field_validator("source_info")
    @classmethod
    def validate_source_info(cls, value):
        if not value or not value.strip():
            raise ValueError("Source info is required and cannot be empty")
        return value.strip()

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value):
        if not value or not value.strip():
            raise ValueError("Tags are required and cannot be empty")
        return value.strip()

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
        return value.strip()

    @field_validator("topic_ids")
    @classmethod
    def validate_topic_ids(cls, value):
        if not value or not value.strip():
            raise ValueError("Topic ID list cannot contain empty values")
        return value

    @field_validator("username")
    @classmethod
    def validate_username(cls, value):
        if not value or not value.strip():
            raise ValueError("Username is required and cannot be empty")
        return value

    @classmethod
    def as_form(
        cls,
        title: str = Form(...),
        description: str = Form(...),
        source: Optional[str] = Form(""),
        source_info: str = Form(...),
        source_data: Optional[str] = Form(""),
        tags: str = Form(...),
        created_by: str = Form(...),
        version: Optional[str] = Form(""),
        topic_ids: str = Form(...),
        level: str = Form(...),
        key_name: Optional[str] = Form(""),
        username: str = Form(...),
    ):
        return cls(
            title=title,
            description=description,
            source=source,
            source_info=source_info,
            source_data=source_data,
            tags=tags,
            created_by=created_by,
            version=version,
            topic_ids=topic_ids,
            level=level,
            key_name=key_name,
            username=username,
        )


CreateContentRequest.__validators__ = {
    "validate_title": CreateContentRequest.validate_title,
    "validate_description": CreateContentRequest.validate_description,
    "validate_source_info": CreateContentRequest.validate_source_info,
    "validate_topic_ids": CreateContentRequest.validate_topic_ids,
    "validate_created_by": CreateContentRequest.validate_created_by,
    "validate_level": CreateContentRequest.validate_level,
    "validate_tags": CreateContentRequest.validate_tags,
    "validate_username": CreateContentRequest.validate_username,
}


def validate_file(file: Optional[UploadFile] = None):
    if file is None or isinstance(file, str):
        return None
    file_extension = file.filename.split(".")[-1].lower()

    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {file_extension}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    return file


# edit content request
EditContentRequestModel: Type = create_model(
    "EditContentRequestModel", **edit_content_fields
)


class EditContentRequest(EditContentRequestModel):
    @model_validator(mode="before")
    @classmethod
    def check_required_fields(cls, values):
        required_fields = [
            "id",
            "title",
            "description",
            "tags",
            "topic_ids",
            "status",
            "updated_by",
        ]
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
            raise ValueError("Id is required and cannot be empty")
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

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value):
        if not value or not value.strip():
            raise ValueError("Tags are required and cannot be empty")
        return value

    @field_validator("topic_ids")
    @classmethod
    def validate_topic_ids(cls, value):
        if not value or not value.strip():
            raise ValueError("Topic ID list cannot contain empty values")
        return value

    @field_validator("status")
    @classmethod
    def validate_status(cls, value):
        allowed_values = set(CONTENT_STATUS["l3"].values())
        if not value or not value.strip():
            raise ValueError("Status is required and cannot be empty")
        if value is not None and value not in allowed_values:
            raise ValueError(
                f"Invalid status type. Allowed values are: {', '.join(allowed_values)}."
            )
        return value

    @field_validator("updated_by")
    @classmethod
    def validate_updated_by(cls, value):
        if not value or not value.strip():
            raise ValueError("Modifier id is required and cannot be empty")
        return value


EditContentRequest.__validators__ = {
    "validate_id": EditContentRequest.validate_id,
    "validate_title": EditContentRequest.validate_title,
    "validate_description": EditContentRequest.validate_description,
    "validate_tags": EditContentRequest.validate_tags,
    "validate_topic_ids": EditContentRequest.validate_topic_ids,
    "validate_status": EditContentRequest.validate_status,
    "validate_updated_by": EditContentRequest.validate_updated_by,
}


# Load all contents request
GetContentRequestModel: Type = create_model("GetContentRequest", **get_content_fields)


class GetContentRequest(GetContentRequestModel):
    pass


ParseContentRequestModel: Type = create_model(
    "ParseContentRequest", **parse_content_fields
)


class ParseContentRequest(ParseContentRequestModel):
    @field_validator("content_id")
    @classmethod
    def validate_content_id(cls, value):
        if not value or not value.strip():
            raise ValueError("Content Id is required and cannot be empty")
        return value.strip()

    @classmethod
    def as_form(
        cls,
        content_id: str = Form(...),
        url: Optional[str] = Form(""),
        page_no: Optional[str] = Form(""),
    ):
        return cls(
            content_id=content_id,
            url=url,
            page_no=page_no,
        )

    pass
