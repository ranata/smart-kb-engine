from helpers.service import print_log, upload_docs_to_s3
from connection.postgres import (
    close_connection,
    get_db_engine,
    load_all_tables,
)
from connection.milvus import create_or_load_db, create_or_load_collection
from config.constants import (
    GLOBAL_DATABASE_NAME,
    CONTENTS_TABLE_NAME,
    LEVEL_LIST_DEFAULT_CONTENT_STATUS,
    TOPICS_TABLE_NAME,
    LEVEL_NAMES,
    CONTENT_STATUS,
    AWS_REGION,
    COGNITO_POOL_ID,
    KB_LLM_SERVICE_URL,
    MILVUS_DATABASE_NAME,
    MILVUS_CONTENT_COLLECTION_NAME,
)
from helpers.service import get_result_in_json, get_signed_url, call_async_api
from fastapi import HTTPException, status, UploadFile, BackgroundTasks
from request_types.contents import (
    CreateContentRequest,
    GetContentRequest,
    EditContentRequest,
)
from sqlalchemy.sql.expression import nulls_last
from sqlalchemy import func, desc
import boto3
import uuid
import os

metadataCollection = load_all_tables()

cognito_client = boto3.client("cognito-idp", region_name=AWS_REGION)


def create_content(
    request: CreateContentRequest,
    file: UploadFile,
    backgroundTask: BackgroundTasks,
    authorization: str,
):
    db, engine = None, None
    try:
        print_log("create_content", "POST", "entry", request)
        db, engine = get_db_engine()

        if db is None:
            print(f"Failed to connect to database '{GLOBAL_DATABASE_NAME}'.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to connect to database '{GLOBAL_DATABASE_NAME}'.",
            )

        topic_ids = request.topic_ids
        topic_ids_list = list(map(int, topic_ids.split(",")))
        unique_id = uuid.uuid4().hex
        location = None
        if file and hasattr(file, "filename") and file.filename:
            filename, extension = os.path.splitext(file.filename)
            uploade_file_url, location = upload_docs_to_s3(
                file, filename, unique_id, extension, request
            )

        request_data_for_content = {
            "title": request.title,
            "source": request.source if request.source else location,
            "source_info": request.source_info,
            "source_data": request.source_data,
            "description": request.description,
            "tags": request.tags,
            "created_by": request.created_by,
            "status": LEVEL_LIST_DEFAULT_CONTENT_STATUS[f"{request.level}"],
            "version": request.version,
            "topic_ids": topic_ids_list,
            "is_deleted": False,
            "updated_at": func.now(),
            **({"approved_time": func.now()} if request.level in ["l1", "l2"] else {}),
        }

        print("request_data_for_content::::", request_data_for_content)

        contents_table = metadataCollection.tables[CONTENTS_TABLE_NAME]
        new_record_id = db.execute(
            contents_table.insert()
            .values(request_data_for_content)
            .returning(contents_table.c.id)
        ).scalar()  # Fetch the returned ID

        db.commit()

        close_connection(db, engine)

        # Migrate knowledge base data
        if LEVEL_LIST_DEFAULT_CONTENT_STATUS[f"{request.level}"] == "ACCEPTED":
            source_mb = request.source if request.source else location
            print("source_mb: ", source_mb)
            if source_mb:
                path = "/".join(source_mb.split("/")[-4:])
                print("path: ", path)
                signed_url = get_signed_url(path)
                request_for_parsing_data = {
                    "content_id": str(new_record_id),
                    "url": signed_url,
                }
                headers = {
                    "Authorization": authorization,
                    "Content-Type": "application/x-www-form-urlencoded",
                }
                backgroundTask.add_task(
                    call_async_api,
                    KB_LLM_SERVICE_URL + "/parse-contents",
                    request_for_parsing_data,
                    headers,
                )

        print_log("create_content", "POST", "exit", "Content created successfully")

        return {
            "data": "Content created successfully",
            "error": None,
        }
    except Exception as e:
        print_log(
            "create_content",
            "POST",
            "error",
            f"Error occurred while creating content: {e}",
        )
        if db:
            db.rollback()
        close_connection(db, engine)
        return {"data": None, "error": str(e)}


def get_contents(request: GetContentRequest):
    db, engine = None, None
    try:
        print_log("get_contents", "POST", "entry", request)
        db, engine = get_db_engine()

        if db is None:
            print(f"Failed to connect to database '{GLOBAL_DATABASE_NAME}'.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to connect to database '{GLOBAL_DATABASE_NAME}'.",
            )

        topics_table = metadataCollection.tables[TOPICS_TABLE_NAME]
        contents_table = metadataCollection.tables[CONTENTS_TABLE_NAME]

        # Extract relevant filters dynamically based on LEVEL_NAMES
        filters = [topics_table.c.is_deleted == False]
        for level in LEVEL_NAMES:
            value = getattr(request, level, None)
            if value:
                value = [item.strip() for item in value.split(",")]
                filters.append(topics_table.c[level].in_(value))
            elif (
                request.tenant and not request.facility
            ):  # make sure it should change according to levele name
                pass
            else:
                filters.append(topics_table.c[level] == "ALL")

        # Build query dynamically based on filters
        query = topics_table.select().with_only_columns(topics_table.c.id)

        if filters:
            query = query.where(
                *filters,
            )

        topic_list_data = db.execute(query).fetchall()
        topic_list_data = get_result_in_json(topics_table, topic_list_data)

        topic_ids = []
        if len(topic_list_data) > 0:
            topic_ids = [int(row["id"]) for row in topic_list_data]

        # Extract relavnt contents based on topic_ids
        content_filters = [contents_table.c.is_deleted == False]
        if topic_ids:
            content_filters.append(contents_table.c.topic_ids.overlap(topic_ids))
        else:
            return {
                "data": [],
                "error": None,
            }

        # Build query dynamically based on filters
        content_query = contents_table.select()

        if filters:
            content_query = content_query.where(
                *content_filters,
            )

        content_query = content_query.order_by(
            nulls_last(desc(contents_table.c.updated_at))
        )
        content_list_data = db.execute(content_query).fetchall()
        content_list_data = get_result_in_json(contents_table, content_list_data)

        close_connection(db, engine)
        print_log("get_contents", "POST", "exit", "Content list fetched successfully")

        return {
            "data": content_list_data,
            "error": None,
        }
    except Exception as e:
        print_log(
            "get_contents",
            "POST",
            "error",
            f"Error occurred while getting contents: {e}",
        )
        if db:
            db.rollback()
        close_connection(db, engine)
        return {"data": None, "error": str(e)}


def view_content(id: int):
    db, engine = None, None
    try:
        print_log("view_content", "POST", "entry", {"id": id})
        db, engine = get_db_engine()

        if db is None:
            print(f"Failed to connect to database '{GLOBAL_DATABASE_NAME}'.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to connect to database '{GLOBAL_DATABASE_NAME}'.",
            )

        contents_table = metadataCollection.tables[CONTENTS_TABLE_NAME]
        content_filters = [
            contents_table.c.is_deleted == False,
            contents_table.c.id == id,
        ]

        # Build query dynamically based on filters
        content_query = contents_table.select().where(
            *content_filters,
        )
        content_data = db.execute(content_query).fetchall()
        content_data = get_result_in_json(contents_table, content_data)

        signed_url = None
        user_details = None
        update_user_details = None
        if len(content_data) > 0:
            content_data = content_data[0]

            if content_data["source"]:
                path = "/".join(content_data["source"].split("/")[-4:])
                print(path)
                signed_url = get_signed_url(path)

            print(content_data["created_by"])
            if content_data["created_by"]:
                try:
                    response = cognito_client.admin_get_user(
                        UserPoolId=COGNITO_POOL_ID,
                        Username=content_data["created_by"],
                    )

                    user_details = {
                        attr["Name"].replace("custom:", ""): attr["Value"]
                        for attr in response["UserAttributes"]
                    }

                    print("content_data:::", user_details)
                except Exception as e:
                    print("cognito user::", str(e))

            if (
                content_data["updated_by"] is not None
                and content_data["created_by"] != content_data["updated_by"]
            ):
                if content_data["updated_by"]:
                    try:
                        response_2 = cognito_client.admin_get_user(
                            UserPoolId=COGNITO_POOL_ID,
                            Username=content_data["updated_by"],
                        )

                        update_user_details = {
                            attr2["Name"].replace("custom:", ""): attr2["Value"]
                            for attr2 in response_2["UserAttributes"]
                        }
                    except Exception as e:
                        print("cognito user::", str(e))
            elif content_data["created_by"] == content_data["updated_by"]:
                update_user_details = user_details

        else:
            return {"data": None, "error": None}

        close_connection(db, engine)
        print_log("view_content", "POST", "exit", {"id": id})

        return {
            "data": {
                **content_data,
                "s3_source_url": signed_url,
                "create_user_data": user_details,
                "update_user_data": update_user_details,
            },
            "error": None,
        }
    except Exception as e:
        print_log(
            "view_content",
            "POST",
            "error",
            f"Error occurred while view content: {e}",
        )
        if db:
            db.rollback()
        close_connection(db, engine)
        return {"data": None, "error": str(e)}


def edit_content(
    request: EditContentRequest, backgroundTask: BackgroundTasks, authorization
):
    db, engine = None, None
    try:
        print_log("edit_content", "POST", "entry", request)
        db, engine = get_db_engine()

        if db is None:
            print(f"Failed to connect to database '{GLOBAL_DATABASE_NAME}'.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to connect to database '{GLOBAL_DATABASE_NAME}'.",
            )

        contents_table = metadataCollection.tables[CONTENTS_TABLE_NAME]
        content_filters = [
            contents_table.c.is_deleted == False,
            contents_table.c.id == int(request.id),
        ]

        # Build query dynamically based on filters
        content_query = (
            contents_table.select()
            .with_only_columns(
                contents_table.c.status,
                contents_table.c.source,
                contents_table.c.stored_in_kb,
            )
            .where(
                *content_filters,
            )
        )
        exist_content_data = db.execute(content_query).mappings().fetchall()

        topic_ids = request.topic_ids
        topic_ids_list = list(map(int, topic_ids.split(",")))

        status_time_fields = {
            CONTENT_STATUS["l3"]["2"]: "review_date",
            CONTENT_STATUS["l3"]["3"]: "approved_time",
            CONTENT_STATUS["l3"]["4"]: "rejected_time",
        }

        request_data_for_content = {
            "title": request.title,
            "description": request.description,
            "tags": request.tags,
            "topic_ids": topic_ids_list,
            "version": request.version,
            "status": request.status,
            "updated_at": func.now(),
            "updated_by": request.updated_by,
        }

        if request.status in status_time_fields:
            request_data_for_content[status_time_fields[request.status]] = func.now()

        print("request_update_data_for_content::", request_data_for_content)
        db.execute(
            contents_table.update()
            .where(contents_table.c.id == int(request.id))
            .values(request_data_for_content)
        )
        db.commit()

        close_connection(db, engine)

        # Update Data in Milvus
        create_or_load_db(MILVUS_DATABASE_NAME)
        collection = create_or_load_collection(MILVUS_CONTENT_COLLECTION_NAME)

        if (
            len(exist_content_data) > 0
            and exist_content_data[0]["status"] == "ACCEPTED"
            and exist_content_data[0]["stored_in_kb"] == "STORED"
        ):
            content_id = request.id
            # Step 1: Retrieve all existing records with the given content_id
            search_expr = (
                f"content_id == '{content_id}'"  # Ensure it's treated as a string
            )
            results = collection.query(
                search_expr,
                output_fields=[
                    "text",
                    "embedding",
                    "summary",
                    "topics",
                    "questions",
                    "named_entities",
                    "metadata",
                    "content_id",
                    "is_deleted",
                ],
            )

            if not results:
                print(f"No records found with content_id: {content_id}")
            else:
                # Step 2: Delete all records with the given content_id
                delete_expr = f"content_id == '{content_id}'"
                collection.delete(delete_expr)
                print(f"Deleted {len(results)} records with content_id: {content_id}")

                # Step 3: Reinsert updated records
                insert_data = [
                    [] for _ in range(10)
                ]  # Same format as your insert function

                for record in results:
                    updated_metadata = {
                        "page": record["metadata"]["page"],  # Keep existing page value
                        "title": request.title,  # Update title
                        "version": request.version,  # Update version
                        "tags": request.tags,  # Update tags
                    }

                    insert_data[0].append(record["text"])
                    insert_data[1].append(record["embedding"])
                    insert_data[2].append(record["summary"])
                    insert_data[3].append(record["topics"])
                    insert_data[4].append(record["questions"])
                    insert_data[5].append(record["named_entities"])
                    insert_data[6].append(updated_metadata)
                    insert_data[7].append(topic_ids_list)
                    insert_data[8].append(record["content_id"])
                    insert_data[9].append(False)

                collection.insert(insert_data)
                print(
                    f"Reinserted {len(results)} records with updated topic_ids for content_id: {content_id}"
                )

                # Step 4: Flush to persist changes
                collection.flush()

                # Step 6: Fetch the newly inserted records to verify the update
                updated_results = collection.query(
                    search_expr, output_fields=["metadata", "topic_ids", "content_id"]
                )

                print(f"Updated Records for content_id {content_id}:")
                for record in updated_results:
                    print(record)

        print_log("edit_content", "POST", "exit", "Content updated successfully")

        if (
            len(exist_content_data) > 0
            and exist_content_data[0]["status"] != "ACCEPTED"
            and request.status == "ACCEPTED"
        ):
            # Migrate knowledge base data
            exist_content_data = exist_content_data[0]
            source_mb = exist_content_data["source"]
            if source_mb:
                path = "/".join(source_mb.split("/")[-4:])
                print("path: ", path)
                signed_url = get_signed_url(path)
                request_for_parsing_data = {
                    "content_id": str(request.id),
                    "url": signed_url,
                }
                headers = {
                    "Authorization": authorization,
                    "Content-Type": "application/x-www-form-urlencoded",
                }
                backgroundTask.add_task(
                    call_async_api,
                    KB_LLM_SERVICE_URL + "/parse-contents",
                    request_for_parsing_data,
                    headers,
                )

        return {
            "data": "Content updated successfully",
            "error": None,
        }
    except Exception as e:
        print_log(
            "edit_content",
            "POST",
            "error",
            f"Error occurred while editing content: {e}",
        )
        if db:
            db.rollback()
        close_connection(db, engine)
        return {"data": None, "error": str(e)}


def delete_content(id: str):
    db, engine = None, None
    try:
        print_log("delete_content", "DELETE", "entry", id)
        db, engine = get_db_engine()

        if db is None:
            print(f"Failed to connect to database '{GLOBAL_DATABASE_NAME}'.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to connect to database '{GLOBAL_DATABASE_NAME}'.",
            )

        contents_table = metadataCollection.tables[CONTENTS_TABLE_NAME]

        # Check if the content exists
        query_check = contents_table.select().where(
            contents_table.c.id == int(id), contents_table.c.is_deleted == False
        )
        result = db.execute(query_check).fetchone()

        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Content with id {id} does not exist.",
            )

        query = (
            contents_table.update()
            .where(
                contents_table.c.id == int(id),
            )
            .values(is_deleted=True)
        )

        db.execute(query)
        db.commit()

        # Delete Data from Milvus
        create_or_load_db(MILVUS_DATABASE_NAME)
        collection = create_or_load_collection(MILVUS_CONTENT_COLLECTION_NAME)

        # Delete records where content_id matches
        delete_expr = f"content_id == '{str(id)}'"
        collection.delete(delete_expr)

        print(f"Deleted records from milvus where content_id = {int(id)}")

        close_connection(db, engine)

        print_log(
            "delete_content", "DELETE", "exit", f"Content {id} deleted successfully"
        )

        return {
            "data": "Content deleted successfully",
            "error": None,
        }
    except Exception as e:
        print_log(
            "delete_content",
            "DELETE",
            "error",
            f"Error occurred while deleting content: {e}",
        )
        if db:
            db.rollback()
        close_connection(db, engine)
        return {"data": None, "error": str(e)}
