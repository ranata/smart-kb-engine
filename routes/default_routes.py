from fastapi import APIRouter
from controllers.default_controller import create_default_tables_in_ps_controller
from response_types.default import DefaultTableCreationResponse

router = APIRouter()


@router.post(
    "/create-default-tables-in-ps", response_model=DefaultTableCreationResponse
)
def add_default_tables_in_ps():
    return create_default_tables_in_ps_controller()
