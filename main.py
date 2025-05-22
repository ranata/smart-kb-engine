from fastapi import FastAPI, Request, Depends
from fastapi.security import HTTPBearer
from routes.sample import index
from routes import (
    default_routes,
    topics_routes,
    content_routes,
    search_routes,
    chats_routes,
)
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from config.constants import origins
from connection.postgres import get_db_engine
from pydantic import ValidationError
from fastapi.openapi.utils import get_openapi

security = HTTPBearer()  # This will handle the token extraction from headers
app = FastAPI()


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Knowledge Base LLM API",
        version="1.0.0",
        description="Custom OpenAPI schema",
        routes=app.routes,
    )

    # Modify the default validation error schema for all endpoints
    for path in openapi_schema["paths"].values():
        for method in path.values():
            responses = method.get("responses", {})
            if "422" in responses:
                responses["422"] = {
                    "description": "Validation Error",
                    "content": {
                        "application/json": {
                            "example": {"detail": "string"},
                            "schema": {
                                "type": "object",
                                "properties": {"detail": {"type": "string"}},
                            },
                        }
                    },
                }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


# It will load env varibles
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allows specific origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allows all headers
)


# For validation exception handler
@app.exception_handler(RequestValidationError)
@app.exception_handler(ValidationError)  # Catching Pydantic validation errors
async def validation_exception_handler(request: Request, exc: Exception):
    errors = (
        exc.errors()
        if isinstance(exc, (RequestValidationError, ValidationError))
        else []
    )
    error_message = errors[0]["msg"] if errors else "Invalid request data."

    return JSONResponse(
        status_code=422,
        content={"detail": error_message},
    )


if get_db_engine():
    print({"message": "Postgres connection successfully"})
else:
    print({"message": "Postgres connection failed"})

app.openapi = custom_openapi

app.include_router(index.router, tags=["Sample"])
app.include_router(
    default_routes.router, tags=["Default"], dependencies=[Depends(security)]
)
app.include_router(
    search_routes.router, tags=["Search"], dependencies=[Depends(security)]
)
app.include_router(
    chats_routes.router, tags=["Chats"], dependencies=[Depends(security)]
)
app.include_router(
    topics_routes.router, tags=["Topics"], dependencies=[Depends(security)]
)
app.include_router(
    content_routes.router, tags=["Contents"], dependencies=[Depends(security)]
)
