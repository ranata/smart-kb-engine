from request_types.chats import ListChatThreadsRequest
from helpers.service import print_log
from connection.postgres import get_db_engine, close_connection, load_all_tables
from config.constants import USER_CONVERSATION_TABLE_NAME, GLOBAL_DATABASE_NAME
from fastapi import HTTPException, status
from sqlalchemy.sql.expression import nulls_last
from sqlalchemy import desc

metadataCollection = load_all_tables()


def list_chat_threads(request: ListChatThreadsRequest):
    db, engine = None, None
    try:
        print_log("list_chat_threads", "POST", "entry", request)
        db, engine = get_db_engine()
        if db is None:
            print(f"Failed to connect to database '{GLOBAL_DATABASE_NAME}'.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to connect to database '{GLOBAL_DATABASE_NAME}'.",
            )
        user_conversation_table = metadataCollection.tables[
            USER_CONVERSATION_TABLE_NAME
        ]
        filters = [user_conversation_table.c.username == request.username]

        # Order by updated_at DESC
        query = (
            user_conversation_table.select()
            .where(*filters)
            .order_by(nulls_last(desc(user_conversation_table.c.created_at)))
        )

        chat_threads_list_data = db.execute(query).mappings().fetchall()

        print_log("list_chat_threads", "POST", "exit", "Chat threads list successfully")
        return {
            "data": chat_threads_list_data,
            "error": None,
        }
    except Exception as e:
        print_log(
            "list_chat_threads",
            "POST",
            "error",
            f"Error occurred while searching knowledge base: {e}",
        )
        if db:
            db.rollback()
        close_connection(db, engine)
        return {"data": None, "code": 400, "error": str(e)}
