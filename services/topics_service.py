import hashlib
from sqlalchemy import desc
from request_types.topics import AddTopicRequest, EditTopicRequest, GetTopicRequest
from connection.postgres import (
    close_connection,
    get_db_engine,
    load_all_tables,
)
from sqlalchemy import func
from config.constants import (
    TOPICS_TABLE_NAME,
    GLOBAL_DATABASE_NAME,
    LEVEL_NAMES,
    CONTENTS_TABLE_NAME,
    AWS_REGION,
    COGNITO_POOL_ID,
)
from helpers.service import get_result_in_json, print_log
from sqlalchemy.sql.expression import nulls_last
from fastapi import HTTPException, status
from sqlalchemy import update
import boto3

metadataCollection = load_all_tables()

cognito_client = boto3.client("cognito-idp", region_name=AWS_REGION)


def create_topics(request: AddTopicRequest):
    db, engine = None, None
    try:
        print_log("create_topics", "POST", "entry", request)
        db, engine = get_db_engine()

        if db is None:
            print(f"Failed to connect to database '{GLOBAL_DATABASE_NAME}'.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to connect to database '{GLOBAL_DATABASE_NAME}'.",
            )

        collection_name = hashlib.md5(request.title.lower().encode()).hexdigest()[:16]
        topics_table = metadataCollection.tables[TOPICS_TABLE_NAME]

        request_data_for_topic = {
            "title": request.title,
            "description": request.description,
            "collection_name": collection_name,
            "level": request.level,
            "is_deleted": False,
            "created_by": request.created_by,
            "updated_at": func.now(),
        }

        for key_name in LEVEL_NAMES:
            if hasattr(request, key_name) and getattr(request, key_name):
                request_data_for_topic[key_name] = getattr(request, key_name)
            else:
                request_data_for_topic[key_name] = "ALL"

        db.execute(topics_table.insert().values(request_data_for_topic))
        db.commit()

        close_connection(db, engine)

        print_log("create_topics", "POST", "exit", request)

        return {
            "data": "Topic created successfully",
            "error": None,
        }
    except Exception as e:
        print_log(
            "create_topics", "POST", "error", f"Error occured while creating topic: {e}"
        )
        if db:
            db.rollback()
        close_connection(db, engine)
        return {"data": None, "error": str(e)}


def edit_topics(request: EditTopicRequest):
    db, engine = None, None
    try:
        print_log("edit_topics", "POST", "entry", request)
        db, engine = get_db_engine()

        if db is None:
            print(f"Failed to connect to database '{GLOBAL_DATABASE_NAME}'.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to connect to database '{GLOBAL_DATABASE_NAME}'.",
            )

        topics_table = metadataCollection.tables[TOPICS_TABLE_NAME]

        request_data_for_topic = {
            "title": request.title,
            "description": request.description,
            "level": request.level,
            "is_deleted": False,
            "updated_by": request.updated_by,
            "updated_at": func.now(),
        }

        for key_name in LEVEL_NAMES:
            if hasattr(request, key_name) and getattr(request, key_name):
                request_data_for_topic[key_name] = getattr(request, key_name)
            else:
                request_data_for_topic[key_name] = "ALL"

        db.execute(
            topics_table.update()
            .where(topics_table.c.id == int(request.id))
            .values(request_data_for_topic)
        )
        db.commit()

        close_connection(db, engine)
        print_log("edit_topics", "POST", "exit", "Topic updated successfully")
        return {
            "data": "Topic updated successfully",
            "error": None,
        }
    except Exception as e:
        print_log(
            "edit_topics", "POST", "error", f"Error occured while updating topic: {e}"
        )
        if db:
            db.rollback()
        close_connection(db, engine)
        return {
            "data": None,
            "error": "Error occured while updating topic:" + str(e),
        }


def get_topics_list(request: GetTopicRequest):
    db, engine = None, None
    try:
        print_log("get_topics_list", "POST", "entry", request)
        db, engine = get_db_engine()

        if db is None:
            print(f"Failed to connect to database '{GLOBAL_DATABASE_NAME}'.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to connect to database '{GLOBAL_DATABASE_NAME}'.",
            )

        topics_table = metadataCollection.tables[TOPICS_TABLE_NAME]
        # Extract relevant filters dynamically based on LEVEL_NAMES
        filters = [topics_table.c.is_deleted == False]
        if request.is_all is not True:
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
        query = topics_table.select()

        if filters:
            query = query.where(
                *filters,
            )

        # Order by updated_at DESC
        query = query.order_by(nulls_last(desc(topics_table.c.updated_at)))

        topic_list_data = db.execute(query).fetchall()

        topic_list_data = get_result_in_json(topics_table, topic_list_data)

        close_connection(db, engine)
        print_log("get_topics_list", "POST", "exit", "topic list fetched successfully")
        return {
            "data": topic_list_data,
            "error": None,
        }

    except Exception as e:
        print_log(
            "get_topics_list",
            "POST",
            "error",
            f"Error occurred while getting topics: {e}",
        )
        if db:
            db.rollback()
        close_connection(db, engine)
        return {"data": None, "error": str(e)}


def delete_topic(id: str):
    db, engine = None, None
    try:
        print_log("delete_topic", "DELETE", "entry", id)
        db, engine = get_db_engine()

        if db is None:
            print(f"Failed to connect to database '{GLOBAL_DATABASE_NAME}'.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to connect to database '{GLOBAL_DATABASE_NAME}'.",
            )

        topics_table = metadataCollection.tables[TOPICS_TABLE_NAME]
        contents_table = metadataCollection.tables[CONTENTS_TABLE_NAME]

        # Check if the topic exists
        query_check = topics_table.select().where(
            topics_table.c.id == int(id), topics_table.c.is_deleted == False
        )
        result = db.execute(query_check).fetchone()
        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Topic with id {id} does not exist.",
            )

        content_filters = [contents_table.c.is_deleted == False]
        if id:
            content_filters.append(contents_table.c.topic_ids.contains([int(id)]))

        content_data_based_on_topic_query = contents_table.select().where(
            *content_filters
        )
        content_list_data = (
            db.execute(content_data_based_on_topic_query).mappings().fetchall()
        )

        has_single_content = any(
            len(item["topic_ids"]) == 1 for item in content_list_data
        )

        if has_single_content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This topic is used in some content as the only topic and cannot be removed.",
            )

        query = (
            topics_table.update()
            .where(
                topics_table.c.id == int(id),
            )
            .values(is_deleted=True)
        )

        db.execute(query)
        db.commit()

        # remove from content
        for row in content_list_data:
            updated_topics = [tid for tid in row["topic_ids"] if tid != int(id)]

            # Update database record
            update_query = (
                update(contents_table)
                .where(contents_table.c.id == row["id"])
                .values(topic_ids=updated_topics)
            )
            db.execute(update_query)
            db.commit()

        close_connection(db, engine)

        print_log("delete_topic", "DELETE", "exit", f"Topic {id} deleted successfully")

        return {
            "data": "Topic deleted successfully",
            "error": None,
        }
    except Exception as e:
        print_log(
            "delete_topic",
            "DELETE",
            "error",
            f"Error occurred while deleting topic: {e}",
        )
        if db:
            db.rollback()
        close_connection(db, engine)
        return {"data": None, "error": str(e)}


def view_topic(id: str):
    db, engine = None, None
    try:
        print_log("view_topic", "GET", "entry", id)
        db, engine = get_db_engine()

        if db is None:
            print(f"Failed to connect to database '{GLOBAL_DATABASE_NAME}'.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to connect to database '{GLOBAL_DATABASE_NAME}'.",
            )

        topics_table = metadataCollection.tables[TOPICS_TABLE_NAME]
        topic_filters = [
            topics_table.c.is_deleted == False,
            topics_table.c.id == id,
        ]

        # Build query dynamically based on filters
        topic_query = topics_table.select().where(
            *topic_filters,
        )
        topic_data = db.execute(topic_query).fetchall()
        topic_data = get_result_in_json(topics_table, topic_data)

        user_details = None
        update_user_details = None
        if len(topic_data) > 0:
            topic_data = topic_data[0]

            if topic_data["created_by"]:
                try:
                    response = cognito_client.admin_get_user(
                        UserPoolId=COGNITO_POOL_ID,
                        Username=topic_data["created_by"],
                    )

                    user_details = {
                        attr["Name"].replace("custom:", ""): attr["Value"]
                        for attr in response["UserAttributes"]
                    }
                except Exception as e:
                    print("cognito user::", str(e))

            if (
                topic_data["updated_by"] is not None
                and topic_data["created_by"] != topic_data["updated_by"]
            ):
                if topic_data["updated_by"]:
                    try:
                        response_2 = cognito_client.admin_get_user(
                            UserPoolId=COGNITO_POOL_ID,
                            Username=topic_data["updated_by"],
                        )

                        update_user_details = {
                            attr2["Name"].replace("custom:", ""): attr2["Value"]
                            for attr2 in response_2["UserAttributes"]
                        }
                    except Exception as e:
                        print("cognito user::", str(e))
            elif topic_data["created_by"] == topic_data["updated_by"]:
                update_user_details = user_details

        else:
            return {"data": None, "error": None}

        close_connection(db, engine)
        print_log("view_topic", "GET", "exit", {"id": id})

        return {
            "data": {
                **topic_data,
                "create_user_data": user_details,
                "update_user_data": update_user_details,
            },
            "error": None,
        }

    except Exception as e:
        print_log(
            "view_topic",
            "GET",
            "error",
            f"Error occurred while view topic: {e}",
        )
        if db:
            db.rollback()
        close_connection(db, engine)
        return {"data": None, "error": str(e)}
