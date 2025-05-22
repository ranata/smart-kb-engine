from fastapi import (
    APIRouter,
    UploadFile,
    Depends,
    HTTPException,
    status,
    BackgroundTasks,
    Header,
)
from controllers.content_controller import (
    fetch_scrape_content_controller,
    create_content_controller,
    get_contents_controller,
    view_content_controller,
    edit_content_controller,
    delete_content_controller,
    parse_content_controller,
)
from request_types.contents import (
    ScrapeDataRequest,
    CreateContentRequest,
    GetContentRequest,
    EditContentRequest,
    ParseContentRequest,
    validate_file,
)
from response_types.content import (
    ScrapeContentResponse,
    CreateContentResponse,
    GetContentResponse,
    ViewContentResponse,
    EditContentResponse,
    DeleteContentResponse,
    ParseContentResponse,
)
from typing import Optional
from middleware.auth import AuthenticatedUser, get_authenticated_user
from helpers.service import validate_user_able_peform_this_operation


router = APIRouter()


@router.post("/scrape-content", response_model=ScrapeContentResponse)
async def scrape_data(data: ScrapeDataRequest):
    return await fetch_scrape_content_controller(data)


@router.post("/create-content", response_model=CreateContentResponse)
async def create_content(
    bgt: BackgroundTasks,
    form_data: CreateContentRequest = Depends(CreateContentRequest.as_form),
    file: Optional[UploadFile] = Depends(validate_file),
    authorization: str = Header(None),
):
    return await create_content_controller(form_data, file, bgt, authorization)


@router.post("/edit-content", response_model=EditContentResponse)
async def edit_content(
    bgt: BackgroundTasks,
    data: EditContentRequest,
    auth_user: AuthenticatedUser = Depends(get_authenticated_user),
    authorization: str = Header(None),
):
    authority = validate_user_able_peform_this_operation(auth_user.groups)
    if not authority:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to perform this operation.",
        )
    return edit_content_controller(data, bgt, authorization)


@router.post("/get-contents", response_model=GetContentResponse)
def get_contents(data: GetContentRequest):
    return get_contents_controller(data)


@router.get("/view-content/{id}", response_model=ViewContentResponse)
def view_content(id: int):
    return view_content_controller(id)


@router.delete("/delete-content/{id}", response_model=DeleteContentResponse)
def delete_topic(
    id: str, auth_user: AuthenticatedUser = Depends(get_authenticated_user)
):
    authority = validate_user_able_peform_this_operation(auth_user.groups)
    if not authority:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to perform this operation.",
        )
    return delete_content_controller(id)


@router.post("/parse-contents", response_model=ParseContentResponse)
async def parse_contents(
    formdata: ParseContentRequest = Depends(ParseContentRequest.as_form),
    file: Optional[UploadFile] = Depends(validate_file),
):
    return await parse_content_controller(formdata, file)
