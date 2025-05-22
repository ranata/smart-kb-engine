from schemas.all_schemas import (
    topic_table_schema,
    contents_table_schema,
    user_history_table_schema,
    user_coversation_table_schema,
)
from sqlalchemy import MetaData
from connection.postgres import engine_pool
from connection.milvus import (
    create_or_load_collection,
    create_or_load_db,
)
from config.constants import MILVUS_DATABASE_NAME, MILVUS_CONTENT_COLLECTION_NAME
from schemas.milvus_all_schemas import mv_content_fields
from pymilvus import CollectionSchema, utility, Index


metadata = MetaData()


def add_default_tables_in_postgres_db():
    try:
        engine = engine_pool
        topic_table = topic_table_schema
        contents_table = contents_table_schema
        user_histoy_table = user_history_table_schema
        user_conversation_table = user_coversation_table_schema
        metadata.create_all(
            engine,
            tables=[
                topic_table,
                contents_table,
                user_histoy_table,
                user_conversation_table,
            ],
        )

        try:
            db = create_or_load_db(MILVUS_DATABASE_NAME)
            print("db: ", db)
            collection_schema = CollectionSchema(
                fields=mv_content_fields,
                description=f"{MILVUS_CONTENT_COLLECTION_NAME} collection",
            )

            collection = create_or_load_collection(
                MILVUS_CONTENT_COLLECTION_NAME, collection_schema
            )
            print("collection: ", collection)
        except Exception as e:
            (f"Error occured while creating default milvus tables: {e}")

        return {
            "data": "Tables created successfully",
            "code": 200,
            "error": None,
        }
    except Exception as e:
        print(f"Error occured while creating default tables: {e}")
        return {"data": None, "code": 400, "error": str(e)}
