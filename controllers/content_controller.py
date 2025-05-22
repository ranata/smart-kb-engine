from fastapi import HTTPException, status, UploadFile, BackgroundTasks
from services.scrape_service import (
    scrape_content_data,
    scrape_cloud_data,
    scrape_dropbox_data,
)
from services.content_service import (
    create_content,
    get_contents,
    view_content,
    edit_content,
    delete_content,
)
from request_types.contents import (
    ScrapeDataRequest,
    CreateContentRequest,
    EditContentRequest,
    ParseContentRequest,
)
from services.parsing_service import parse_contents


async def fetch_scrape_content_controller(request: ScrapeDataRequest):
    data = None
    if request.type == "LINK":
        data = await scrape_content_data(request)
    if request.type == "DRIVE":
        data = await scrape_cloud_data(request)
    if request.type == "DROPBOX":
        data = await scrape_dropbox_data(request)
    if data["error"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=data["error"]
        )
    return {"data": data["data"], "status": "success"}


async def create_content_controller(
    request: CreateContentRequest,
    file: UploadFile,
    backgroundTask: BackgroundTasks,
    authorization,
):
    data = create_content(request, file, backgroundTask, authorization)
    if data["error"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=data["error"]
        )
    return {"data": data["data"], "status": "success"}


def edit_content_controller(
    request: EditContentRequest,
    backgroundTask: BackgroundTasks,
    authorization,
):
    data = edit_content(request, backgroundTask, authorization)
    if data["error"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=data["error"]
        )
    return {"data": data["data"], "status": "success"}


def get_contents_controller(request: CreateContentRequest):
    data = get_contents(request)
    if data["error"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=data["error"]
        )
    return {"data": data["data"], "status": "success"}


def view_content_controller(id: int):
    data = view_content(id)
    if data["error"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=data["error"]
        )
    return {"data": data["data"], "status": "success"}


def delete_content_controller(id: int):
    data = delete_content(id)
    if data["error"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=data["error"]
        )
    return {"data": data["data"], "status": "success"}


async def parse_content_controller(request: ParseContentRequest, file: UploadFile):
    data = await parse_contents(request, file)
    if data["error"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=data["error"]
        )
    return {"data": data["data"], "status": "success"}
