import os
from dotenv import load_dotenv

load_dotenv()

ENV = os.environ["ENVIRONMENT"]

# Set global database name based on ENV
GLOBAL_DATABASE_NAME = (
    "global_db" if ENV == "dev" else "qa_global_db" if ENV == "qa" else "prod_global_db"
)
MILVUS_DATABASE_NAME = (
    "dev_ieq_kb_db"
    if ENV == "dev"
    else "qa_ieq_kb_db"
    if ENV == "qa"
    else "prod_ieq_kb_db"
)
KB_LLM_SERVICE_URL = os.environ["KB_LLM_SERVICE_URL"]
MILVUS_CONTENT_COLLECTION_NAME = "contents"
OPEN_API_KEY = os.environ["OPEN_API_KEY"]
AWS_REGION = os.environ["AWS_REGION"]
COGNITO_POOL_ID = os.environ["COGNITO_POOL_ID"]
GOOGLE_API_KEY = os.environ["GOOGLE_API_KEY"]
S3_BUCKET_NAME = os.environ["S3_BUCKET_NAME"]
origins = [
    os.environ.get("SAAS_LOCAL_URL", ""),
    os.environ.get("SAAS_DEV_URL", ""),
    os.environ.get("SAAS_QA_URL", ""),
    os.environ.get("SAAS_PROD_URL", ""),
]
origins = [url for url in origins if url]
LLMA_API_KEY = os.environ["LLMA_API_KEY"]

CONTENTS_TABLE_NAME = "contents"
TOPICS_TABLE_NAME = "topics"
PROMPTS_TABLE_NAME = "prompts"
USER_CHAT_HISTORY_TABLE_NAME = "user_chat_history"
USER_CONVERSATION_TABLE_NAME = "user_conversation"
CHAT_HISTORY_SIZE=3
DEFAULT_POSTGRES_TABLES = ["contents", "topics", "prompts"]
LEVEL_NAMES = [
    "tenant",
    "facility",
]  # make sure this will change according to the projects, it will the level like how many level you want in project for storing topics and content

AUTHORITY_UPDATE_USER_ROLES = ["admin", "tenantAdmin"]

CONTENT_STATUS = {
    "l1": "ACCEPTED",
    "l2": "ACCEPTED",
    "l3": {"1": "DRAFT", "2": "REVIEW", "3": "ACCEPTED", "4": "REJECTED"},
}

LEVEL_LIST_DEFAULT_CONTENT_STATUS = {
    "l1": CONTENT_STATUS["l1"],  # this is for admin
    "l2": CONTENT_STATUS["l2"],  # this is for tenant admin
    "l3": CONTENT_STATUS["l3"]["1"],
}

ALLOWED_EXTENSIONS = {
    "pdf",
    "doc",
    "docx",
    "xlsx",
    "csv",
    "txt",
    "html",
    "ppt",
    "pptx",
    "xls",
    "jpg",
    "jpeg",
    "png",
    "avif",
    "webp",
    "mp4",
}

GOOGLE_MIME_TYPES = {
    "application/vnd.google-apps.document": "pdf",
    "application/vnd.google-apps.spreadsheet": "pdf",
    "application/vnd.google-apps.presentation": "ppt",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "pdf",
}

CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".csv": "text/csv",
    ".txt": "text/plain",
    ".html": "text/html",
    ".ppt": "application/vnd.ms-powerpoint",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".xls": "application/vnd.ms-excel",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".avif": "image/avif",
    ".webp": "image/webp",
    ".mp4": "video/mp4",
}

PROMPT_FOR_TOPICS_QUESTIONS = """Go through the below content and extract the following information in JSON format.
        - Summarize the content highlighting key points in not more than 200 words.
        - Extract upto 3 main topics covered in the content.
        - Extract upto 5 main questions covered in the content.
        - Extract all the names entities mentioned in the content.
    Try to fill JSON key/values only if they are mentioned in the content.
    Do not infer or assume anything. All the information should be picked only from content below "Content Text".
    Do not add any additional commentary.
    In the summary, please do not include commentary like "this content discusses". The summary should only include facts from the content.
    Output should strictly be a JSON.
    Following is the output JSON format:
    {{
        "summary": "<text>",
        "topics": ["<topic1>", "<topic2>", "<topic3>"],
        "questions": ["<question1>", "<question2>", "<question3>", "<question4>", "<question5>"],
        "named_entities": ["<named_entities1>", "<named_entities2>", "<named_entities3>", ...],
    }}"""

EMBEDDING_MODEL_NAME = "text-embedding-ada-002"
LLM_MODEL_NAME = "gpt-3.5-turbo"
