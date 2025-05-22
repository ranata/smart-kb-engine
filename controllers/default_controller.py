from fastapi import HTTPException, status
from services.default_service import add_default_tables_in_postgres_db


def create_default_tables_in_ps_controller():
    data = add_default_tables_in_postgres_db()
    if data["error"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=data["error"]
        )
    return {"data": data["data"], "status": "success"}
