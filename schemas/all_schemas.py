from sqlalchemy import Table, MetaData

from config.constants import (
    TOPICS_TABLE_NAME,
    CONTENTS_TABLE_NAME,
    USER_CHAT_HISTORY_TABLE_NAME,
    USER_CONVERSATION_TABLE_NAME,
)
from schemas.columns import (
    topic_table_columns,
    content_table_columns,
    user_chat_history_columns,
    user_conversation_columns,
)

topic_table_schema = Table(
    TOPICS_TABLE_NAME,
    MetaData(),
    *topic_table_columns,
    extend_existing=True,
)

contents_table_schema = Table(
    CONTENTS_TABLE_NAME,
    MetaData(),
    *content_table_columns,
    extend_existing=True,
)

user_history_table_schema = Table(
    USER_CHAT_HISTORY_TABLE_NAME,
    MetaData(),
    *user_chat_history_columns,
    extend_existing=True,
)

user_coversation_table_schema = Table(
    USER_CONVERSATION_TABLE_NAME,
    MetaData(),
    *user_conversation_columns,
    extend_existing=True,
)
