from config.constants import (
    GLOBAL_DATABASE_NAME,
    CONTENT_TYPES,
    AUTHORITY_UPDATE_USER_ROLES,
    S3_BUCKET_NAME,
)
from connection.postgres import get_engine, DB_NAME
from sqlalchemy.sql import text
from botocore.exceptions import NoCredentialsError
from fastapi import HTTPException
from typing import List
import re
import boto3
import httpx


def get_db_name(request):
    db_name_map = GLOBAL_DATABASE_NAME

    tenant_name = (
        request.tenant_name
        if hasattr(request, "tenant_name") and request.tenant_name
        else "tenant"
    )
    facility_name = (
        request.facility_name
        if hasattr(request, "facility_name") and request.facility_name
        else "facility"
    )

    if tenant_name and request.tenant and facility_name and request.facility:
        db_name_map = (
            f"{tenant_name}_{facility_name}_{request.tenant}_{request.facility}"
        )
    elif tenant_name and request.tenant:
        db_name_map = f"{tenant_name}_{request.tenant}"

    return db_name_map


def get_old_db_name(request):
    db_name_map = GLOBAL_DATABASE_NAME

    old_tenant_name = (
        request.old_tenant_name
        if hasattr(request, "old_tenant_name") and request.old_tenant_name
        else "tenant"
    )
    old_facility_name = (
        request.old_facility_name
        if hasattr(request, "old_facility_name") and request.old_facility_name
        else "facility"
    )

    if (
        old_tenant_name
        and request.old_tenant
        and old_facility_name
        and request.old_facility
    ):
        db_name_map = f"{old_tenant_name}_{old_facility_name}_{request.old_tenant}_{request.old_facility}"
    elif old_tenant_name and request.old_tenant:
        db_name_map = f"{old_tenant_name}_{request.old_tenant}"

    return db_name_map


def create_database_if_not_exists(db_name: str):
    engine = get_engine(DB_NAME)
    conn = engine.connect()
    conn.execution_options(isolation_level="AUTOCOMMIT")

    # Check if the database exists
    result = conn.execute(
        text("SELECT 1 FROM pg_database WHERE datname = :db_name"), {"db_name": db_name}
    ).fetchone()

    if not result:
        conn.execute(f"CREATE DATABASE {db_name};")
        print(f"Database '{db_name}' created successfully.")

    conn.close()
    engine.dispose()


def check_database_is_exists(db_name: str):
    engine = get_engine(DB_NAME)
    conn = engine.connect()
    conn.execution_options(isolation_level="AUTOCOMMIT")

    # Check if the database exists
    result = conn.execute(
        text("SELECT 1 FROM pg_database WHERE datname = :db_name"), {"db_name": db_name}
    ).fetchone()

    if not result:
        conn.close()
        engine.dispose()
        return False

    conn.close()
    engine.dispose()
    return True


def get_result_in_json(table, data):
    column_names = table.columns.keys()
    data_list = [dict(zip(column_names, row)) for row in data]
    return data_list


def print_log(method_name, method_type, event, data):
    print(
        f"{method_name}::",
        {
            "event": event,
            "method": method_type,
            "name": method_name,
            "data": data,
        },
    )


def upload_docs_to_s3(
    file_path: str, file_name: str, unique_id: str, file_ext: str, config
):
    s3_client = boto3.client("s3")
    s3_bucket_name = S3_BUCKET_NAME

    safe_file_name = sanitize_filename(file_name)
    s3_filename = "llm_content_cloud_files/"
    if hasattr(config, "key_name") and config.key_name:
        s3_filename += f"{config.key_name}/{config.username}/"
    else:
        s3_filename += f"global/{config.username}/"

    s3_filename += f"{safe_file_name}_{unique_id}{file_ext}"

    content_type = CONTENT_TYPES[f"{file_ext}"]
    if not content_type:
        content_type = "application/octet-stream"

    try:
        s3_client.upload_fileobj(
            file_path.file,  # Directly pass UploadFile's file object
            s3_bucket_name,
            s3_filename,
            ExtraArgs={"ContentType": content_type},
        )
        signed_url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": s3_bucket_name, "Key": s3_filename},
            ExpiresIn=3600,
        )
        return signed_url, signed_url.split("?")[0]
    except NoCredentialsError:
        raise HTTPException(status_code=400, detail="AWS credentials not available.")


def get_signed_url(s3_filename: str):
    s3_client = boto3.client("s3")
    s3_bucket_name = S3_BUCKET_NAME
    signed_url = s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": s3_bucket_name, "Key": s3_filename},
        ExpiresIn=3600,
    )
    return signed_url


def validate_user_able_peform_this_operation(groups: List[str]):
    return any(role in groups for role in AUTHORITY_UPDATE_USER_ROLES)


async def call_async_api(API_URL: str, data: dict, header):
    async with httpx.AsyncClient(timeout=None) as client:
        try:
            response = await client.post(API_URL, data=data, headers=header)
            print("API Response:", response.json())
        except httpx.RequestError as e:
            print(f"Request error: {str(e)}")
            return {"error": "Request failed"}
        
def sanitize_filename(filename: str) -> str:
    # Replace spaces and special characters with underscores
    sanitized = re.sub(r'[\s,]+', '_', filename)  # Replace spaces and commas with _
    sanitized = re.sub(r'[^a-zA-Z0-9_.]', '_', sanitized)  # Replace other special chars with _
    return sanitized