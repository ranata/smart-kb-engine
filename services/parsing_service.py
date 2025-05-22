from helpers.service import print_log
from connection.postgres import close_connection, load_all_tables, get_db_engine
from connection.milvus import create_or_load_collection, create_or_load_db
from request_types.contents import ParseContentRequest
from fastapi import UploadFile, HTTPException, status
from config.constants import (
    LLMA_API_KEY,
    OPEN_API_KEY,
    PROMPT_FOR_TOPICS_QUESTIONS,
    EMBEDDING_MODEL_NAME,
    LLM_MODEL_NAME,
    MILVUS_CONTENT_COLLECTION_NAME,
    MILVUS_DATABASE_NAME,
    CONTENTS_TABLE_NAME,
)
from llama_index.embeddings.openai import OpenAIEmbedding
from bs4 import BeautifulSoup
import httpx
import openai
import json
import nest_asyncio

nest_asyncio.apply()
from llama_parse import LlamaParse

metadataCollection = load_all_tables()

# openai key configured
client = openai.OpenAI(api_key=OPEN_API_KEY)

MAX_LENGTHS = {
    "text": 20000,
    "summary": 500,
    "topics": 10,
    "questions": 10,
    "named_entities": 500,
}


def get_file_extension(url):
    path = url.split("?")[0]  # Remove query parameters
    filename = path.split("/")[-1]  # Get the last part of the path
    if "." in filename:
        return filename.split(".")[-1]  # Extract the extension
    return None  # No extension found


async def download_file(url):
    async with httpx.AsyncClient(timeout=None) as client:
        response = await client.get(url)
        if response.status_code == 200:
            html_content = response.text
            soup = BeautifulSoup(html_content, "html.parser")
            text = soup.get_text(separator="\n", strip=True)
            return text
        else:
            raise Exception(f"Failed to download file: {response.status_code}")


def truncate_text(text, max_length):
    if not isinstance(text, str):
        return text

    encoded_text = text.encode("utf-8")
    if len(encoded_text) <= max_length:
        return text

    # Find valid truncation point
    truncated = encoded_text[:max_length].decode("utf-8", errors="ignore")
    return truncated


def truncate_list(lst, max_length):
    return lst[:max_length] if isinstance(lst, list) else lst


def process_document(text):
    prompt = (
        PROMPT_FOR_TOPICS_QUESTIONS
        + f"""
    Content Text:
    {text}
    """
    )

    response = client.chat.completions.create(
        model=LLM_MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=1000,
    )

    return json.loads(response.choices[0].message.content)


async def parse_contents(request: ParseContentRequest, file: UploadFile):
    """Parses documents, generates embeddings, and stores them in Milvus."""
    db, engine, parsed_documents = None, None, None
    try:
        print_log("parse_contents", "POST", "entry", request)

        # db connection and content validation
        db, engine = get_db_engine()
        contents_table = metadataCollection.tables[CONTENTS_TABLE_NAME]
        content_filters = [
            contents_table.c.is_deleted == False,
            contents_table.c.id == int(request.content_id),
        ]

        # Build query dynamically based on filters
        content_query = (
            contents_table.select()
            .with_only_columns(
                contents_table.c.title,
                contents_table.c.topic_ids,
                contents_table.c.version,
                contents_table.c.tags,
            )
            .where(
                *content_filters,
            )
        )
        content_data = db.execute(content_query).mappings().fetchall()

        if not content_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Content is not exist or might be deleted",
            )

        content_data = content_data[0]

        content_title, content_topic_ids, content_version, content_tags = (
            content_data["title"],
            content_data["topic_ids"],
            content_data["version"],
            content_data["tags"],
        )

        parser = LlamaParse(
            result_type="markdown",
            api_key=LLMA_API_KEY,
            job_timeout_in_seconds=3000,
            auto_mode=True,
            auto_mode_trigger_on_table_in_page=True,
            auto_mode_trigger_on_image_in_page=True,
        )
        if file:
            print("file: ", file)

            # temp_input_path = "/tmp/input.pdf"

            # with open(temp_input_path, "wb") as buffer:
            #     buffer.write(await file.read())

            # print("parsing started in file........................")
            # parsed_documents = parser.load_data(file_path="/tmp/input.pdf")
            # print("parsing ended in file........................")
        elif request.url:
            print("pasring started in url........................")
            file_ext = get_file_extension(request.url)

            job_id = None
            if file_ext == "html":
                text = await download_file(request.url)
                job_id = await parser._create_job(
                    file_input=text.encode(),  # Convert text to bytes
                    extra_info={"file_name": "content.txt"},  # Pretend it's a text file
                )
            else:
                job_id = await parser._create_job(file_input=request.url)

            if job_id:
                parsed_documents = await parser._get_job_result(
                    job_id=job_id, result_type="json"
                )
                parsed_documents = parsed_documents["pages"]

            print("pasring ended in url........................")

        results = {}
        print("document parsing started............")
        if parsed_documents and len(parsed_documents) > 0:
            parsed_documents = [
                record
                for record in parsed_documents
                if record["md"] != "NO_CONTENT_HERE"
            ]

            for doc in parsed_documents:
                doc_page = doc["page"]
                doc_text = doc["md"]

                results[doc_page] = process_document(doc_text)

            print("document parsing ended............")
            # Transform dictionary results into a list with the required format
            formatted_results = []
            print("document formation started............")
            for doc in parsed_documents:
                doc_page = doc["page"]
                doc_text = doc["md"]

                if doc_page in results:
                    formatted_results.append(
                        {
                            "text": doc_text,
                            "summary": results[doc_page]["summary"],
                            "topics": results[doc_page]["topics"],
                            "questions": results[doc_page]["questions"],
                            "named_entities": results[doc_page]["named_entities"],
                            "topic_ids": content_topic_ids,
                            "content_id": request.content_id,
                            "is_deleted": False,
                            "metadata": {
                                "page": doc_page,
                                "title": content_title,
                                "version": content_version,
                                "tags": content_tags,
                            },
                        }
                    )

            print("document formation ended............")
            # Initialize LlamaIndex with OpenAI Embedding & Milvus
            embed_model = OpenAIEmbedding(
                model=EMBEDDING_MODEL_NAME, api_key=OPEN_API_KEY
            )

            # Insert Data into Milvus
            create_or_load_db(MILVUS_DATABASE_NAME)
            collection = create_or_load_collection(MILVUS_CONTENT_COLLECTION_NAME)
            insert_data = [[] for _ in range(10)]

            print("document embedding started............")
            for doc in formatted_results:
                print("document embedding in loop")
                embedding = embed_model.get_text_embedding(doc["text"])

                insert_data[0].append(truncate_text(doc["text"], MAX_LENGTHS["text"]))
                insert_data[1].append(embedding)
                insert_data[2].append(
                    truncate_text(doc["summary"], MAX_LENGTHS["summary"])
                )
                insert_data[3].append(
                    truncate_list(doc["topics"], MAX_LENGTHS["topics"])
                )
                insert_data[4].append(
                    truncate_list(doc["questions"], MAX_LENGTHS["questions"])
                )
                insert_data[5].append(
                    truncate_list(doc["named_entities"], MAX_LENGTHS["named_entities"])
                )
                insert_data[6].append(doc["metadata"])
                insert_data[7].append(doc["topic_ids"])
                insert_data[8].append(doc["content_id"])
                insert_data[9].append(doc["is_deleted"])

            print("document embedding ended............")
            # Milvus db connection and process
            collection.insert(insert_data)
            print("data inserted embedding............")

            update_data_for_content = {
                "stored_in_kb": "STORED",
            }
            print("update_data_for_content::", update_data_for_content)
            db.execute(
                contents_table.update()
                .where(contents_table.c.id == int(request.content_id))
                .values(update_data_for_content)
            )
            db.commit()

        print_log("parse_contents", "POST", "exit", "data parsed successfully")

        return {
            "data": "data parsed successfully",
            "error": None,
        }
    except Exception as e:
        print_log(
            "parse_contents",
            "POST",
            "error",
            f"Error occurred while parsing content: {e}",
        )
        if db:
            db.rollback()
        close_connection(db, engine)
        return {"data": None, "error": str(e)}
