from request_types.contents import ScrapeDataRequest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from botocore.exceptions import NoCredentialsError
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import uuid
import re
import boto3
import os
import tempfile
import requests
from fastapi import HTTPException
from config.constants import (
    ALLOWED_EXTENSIONS,
    GOOGLE_MIME_TYPES,
    CONTENT_TYPES,
    GOOGLE_API_KEY,
    S3_BUCKET_NAME,
)
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2.credentials import Credentials


s3_client = boto3.client("s3")


# Website Url scrape data service


def fetch_html_with_selenium(url: str):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920x1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    try:
        driver.get(url)
        wait = WebDriverWait(driver, 10)
        wait.until(EC.url_to_be(url))
        final_url = driver.current_url
        html_content = driver.page_source
        return html_content, final_url
    finally:
        driver.quit()


def clean_html(html_content: str, final_url: str):
    html_content = re.sub(
        r'(<img[^>]+src=["\'])(/[^"\']+)(["\'])',
        lambda m: f"{m.group(1)}{urljoin(final_url, m.group(2))}{m.group(3)}",
        html_content,
    )

    html_content = re.sub(
        r'(<link[^>]+href=["\'])(/[^"\']+)(["\'])',
        lambda m: f"{m.group(1)}{urljoin(final_url, m.group(2))}{m.group(3)}",
        html_content,
    )

    html_content = re.sub(
        r'(<script[^>]+src=["\'])(/[^"\']+)(["\'])',
        lambda m: f"{m.group(1)}{urljoin(final_url, m.group(2))}{m.group(3)}",
        html_content,
    )

    html_content = re.sub(r"\n\s*\n+", "\n", html_content).strip()

    return html_content


async def scrape_content_data(request: ScrapeDataRequest):
    try:
        html_content, final_url = fetch_html_with_selenium(request.url)
        cleaned_html = clean_html(html_content, final_url)
        soup = BeautifulSoup(cleaned_html, "html5lib")

        file_name = re.sub(r"\W+", "_", request.url.strip("/"))[:50]
        file_ext = ".html"

        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            tmp_file.write(soup.prettify().encode("utf-8"))
            temp_file_path = tmp_file.name

        unique_id = uuid.uuid4().hex
        signed_url = await upload_to_s3(
            temp_file_path, file_name, unique_id, file_ext, request
        )

        return {
            "data": {
                "url_or_html": signed_url,
                "s3_location": signed_url.split("?")[0],
            },
            "error": None,
        }
    except Exception as e:
        return {
            "data": None,
            "error": str(e),
        }


# End of  Website Url scrape data service


# Google Drive scrape data service


def get_google_drive_file_id(url: str):
    match = re.search(r"(?:/d/|id=)([a-zA-Z0-9_-]+)", url)
    return match.group(1) if match else None


def get_google_drive_service(user_drive_token: str):
    credentials = Credentials(token=user_drive_token)  # Convert string to Credentials
    return build("drive", "v3", credentials=credentials)


def sanitize_filename(file_name):
    base_name, ext = os.path.splitext(file_name)  # Split name and extension
    if ext.lower() not in [f".{e}" for e in ALLOWED_EXTENSIONS]:
        ext = ""  # Remove invalid extension
    return base_name, ext  # Return cleaned name and extension


def get_google_drive_file_metadata(file_id: str):
    metadata_url = f"https://www.googleapis.com/drive/v3/files/{file_id}?fields=name,mimeType&key={GOOGLE_API_KEY}"
    response = requests.get(metadata_url)

    if response.status_code in [403, 404]:
        raise HTTPException(
            status_code=400,
            detail="The provided URL is private and cannot be accessed. Please ensure the file is shared appropriately or check your access permissions.",
        )

    if response.status_code == 200:
        metadata = response.json()

        # Check if the provided link is a folder
        if metadata.get("mimeType") == "application/vnd.google-apps.folder":
            raise HTTPException(
                status_code=400, detail="You have provided a folder link, not a file."
            )

        # Extract file extension
        file_name = metadata.get("name", "")
        _, ext = os.path.splitext(file_name)

        ext = ext.lower().strip(".")

        if ext.strip() == "" and GOOGLE_MIME_TYPES[metadata.get("mimeType")]:
            ext = GOOGLE_MIME_TYPES[metadata.get("mimeType")]
        # Validate file extension
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File type '{ext}' is not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}.",
            )

        return metadata

    raise HTTPException(status_code=400, detail="Could not retrieve file metadata.")


def private_get_google_drive_file_metadata(file_id: str, user_drive_token: str):
    try:
        drive_service = get_google_drive_service(user_drive_token)
        file = (
            drive_service.files().get(fileId=file_id, fields="name, mimeType").execute()
        )
        file_name = file.get("name", "")
        mime_type = file.get("mimeType", "")

        if mime_type == "application/vnd.google-apps.folder":
            raise HTTPException(
                status_code=400, detail="Provided link is a folder, not a file."
            )

        # Determine file extension
        _, ext = os.path.splitext(file_name)
        ext = ext.lower().strip(".")

        if not ext and mime_type in GOOGLE_MIME_TYPES:
            ext = GOOGLE_MIME_TYPES[mime_type]

        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400, detail=f"File type '{ext}' is not allowed."
            )

        return file_name, mime_type, ext
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Error retrieving file metadata: {str(e)}"
        )


def private_download_google_drive_file(file_id: str, user_drive_token: str):
    try:
        file_name, mime_type, file_ext = private_get_google_drive_file_metadata(
            file_id, user_drive_token
        )

        export_formats = {
            "application/vnd.google-apps.document": "application/pdf",
            "application/vnd.google-apps.spreadsheet": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.google-apps.presentation": "application/pdf",
        }

        # Ensure filename is correctly formatted
        base_name, ext = sanitize_filename(
            file_name
        )  # Extract cleaned filename & extension
        unique_id = uuid.uuid4().hex  # Generate unique ID
        final_file_name = f"{base_name}_{unique_id}{ext}"  # Correct format
        temp_file_path = f"/tmp/{final_file_name}"

        drive_service = get_google_drive_service(user_drive_token)

        if mime_type in export_formats:
            export_format = export_formats[mime_type]
            ext = (
                ".xlsx"
                if "spreadsheet" in mime_type
                else f".{export_format.split('/')[-1]}"
            )
            request = drive_service.files().export_media(
                fileId=file_id, mimeType=export_format
            )
        else:
            request = drive_service.files().get_media(fileId=file_id)

        with open(temp_file_path, "wb") as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()

        return temp_file_path, base_name, ext

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error downloading file: {str(e)}")


def download_google_drive_file(file_id: str):
    metadata = get_google_drive_file_metadata(file_id)

    if not metadata:
        raise ValueError("Could not retrieve file metadata.")

    mime_type = metadata["mimeType"]
    original_file_name = metadata["name"]

    base_name, ext = os.path.splitext(original_file_name)

    export_formats = {
        "application/vnd.google-apps.document": "application/pdf",  # Docs → PDF
        "application/vnd.google-apps.spreadsheet": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # Sheets → Excel
        "application/vnd.google-apps.presentation": "application/pdf",  # Slides → PDF
    }

    if mime_type in export_formats:
        export_format = export_formats[mime_type]
        file_ext = (
            ".xlsx"
            if "spreadsheet" in mime_type
            else f".{export_format.split('/')[-1]}"
        )  # Sheets → .xlsx
        download_url = f"https://www.googleapis.com/drive/v3/files/{file_id}/export?mimeType={export_format}&key={GOOGLE_API_KEY}"
    else:
        download_url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media&key={GOOGLE_API_KEY}"
        file_ext = ext if ext else ".unknown"  # Use existing extension if available

    temp_file_path = f"/tmp/{uuid.uuid4().hex}{file_ext}"

    try:
        response = requests.get(download_url, stream=True)

        if response.status_code != 200:
            raise ValueError("Failed to download Google Drive file.")

        with open(temp_file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        return temp_file_path, base_name, file_ext
    except Exception as e:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        raise HTTPException(status_code=400, detail=f"Error downloading file: {str(e)}")


async def upload_to_s3(
    file_path: str, file_name: str, unique_id: str, file_ext: str, config
):
    s3_bucket_name = S3_BUCKET_NAME

    safe_file_name = re.sub(r"[\/\s]+", "_", file_name)
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
        s3_client.upload_file(
            file_path,
            s3_bucket_name,
            s3_filename,
            ExtraArgs={"ContentType": content_type},
        )
        signed_url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": s3_bucket_name, "Key": s3_filename},
            ExpiresIn=3600,
        )
        return signed_url
    except NoCredentialsError:
        raise HTTPException(status_code=400, detail="AWS credentials not available.")


async def scrape_cloud_data(request):
    try:
        drive_url = request.url
        token = request.token
        local_file_path, file_name, file_ext = None, None, None
        if token:
            file_id = get_google_drive_file_id(drive_url)
            if not file_id:
                raise HTTPException(status_code=400, detail="Invalid Google Drive URL")

            # Download the file
            local_file_path, file_name, file_ext = private_download_google_drive_file(
                file_id, request.token
            )
        else:
            file_id = get_google_drive_file_id(drive_url)
            if not file_id:
                raise HTTPException(status_code=400, detail="Invalid Google Drive URL")

            # Download the file
            local_file_path, file_name, file_ext = download_google_drive_file(file_id)

        # Upload to S3
        unique_id = uuid.uuid4().hex
        s3_url = await upload_to_s3(
            local_file_path, file_name, unique_id, file_ext, request
        )

        # Cleanup
        os.remove(local_file_path)

        return {
            "data": {"url_or_html": s3_url, "s3_location": s3_url.split("?")[0]},
            "error": None,
        }
    except Exception as e:
        return {"data": None, "error": str(e)}


# End of Google Drive scrape data service


# Scrape drop box data


def get_dropbox_file_id(url: str):
    match = re.search(r"(www.dropbox.com/s/([^?]+))", url)
    if match:
        return match.group(2)
    return None


def get_dropbox_file_metadata(url: str):
    metadata_url = url.replace("www.dropbox.com", "dl.dropboxusercontent.com")

    response = requests.head(metadata_url)

    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Invalid Dropbox file URL")

    # Extract filename from headers
    content_disposition = response.headers.get("Content-Disposition", "")
    match = re.search(r'filename="(.+)"', content_disposition)
    file_name = match.group(1) if match else "unknown"

    _, ext = os.path.splitext(file_name)

    if ext.lower().strip(".") not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="File type not allowed. Only specific document, image, and video files are supported.",
        )

    return metadata_url, file_name, ext


def download_dropbox_file(file_url: str, file_name: str, file_ext: str):
    temp_file_path = f"/tmp/{uuid.uuid4().hex}{file_ext}"

    try:
        response = requests.get(file_url, stream=True)
        if response.status_code != 200:
            raise ValueError("Failed to download Dropbox file.")

        with open(temp_file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        return temp_file_path, file_name, file_ext
    except Exception as e:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        raise HTTPException(status_code=400, detail=f"Error downloading file: {str(e)}")


async def upload_to_s3_dropbox(
    file_path: str, file_name: str, unique_id: str, file_ext: str, config
):
    s3_bucket_name = S3_BUCKET_NAME
    safe_file_name = re.sub(r"[\/\s]+", "_", file_name)

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
        s3_client.upload_file(
            file_path,
            s3_bucket_name,
            s3_filename,
            ExtraArgs={"ContentType": content_type},
        )
        signed_url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": s3_bucket_name, "Key": s3_filename},
            ExpiresIn=3600,
        )
        return signed_url
    except NoCredentialsError:
        raise HTTPException(status_code=400, detail="AWS credentials not available.")


async def scrape_dropbox_data(request):
    try:
        dropbox_url = request.url
        file_url, file_name, file_ext = get_dropbox_file_metadata(dropbox_url)

        # Download the file
        local_file_path, file_name, file_ext = download_dropbox_file(
            file_url, file_name, file_ext
        )

        # Upload to S3
        unique_id = uuid.uuid4().hex
        s3_url = await upload_to_s3_dropbox(
            local_file_path, file_name, unique_id, file_ext, request
        )

        # Cleanup
        os.remove(local_file_path)

        return {
            "data": {"url_or_html": s3_url, "s3_location": s3_url.split("?")[0]},
            "error": None,
        }
    except Exception as e:
        return {"data": None, "error": str(e)}


# End of Scrape drop box data
