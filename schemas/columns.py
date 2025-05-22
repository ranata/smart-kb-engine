from sqlalchemy import Column, Integer, String, TIMESTAMP, func, Boolean, TEXT
from config.constants import LEVEL_NAMES
from sqlalchemy.dialects.postgresql import ARRAY


topic_table_columns = [
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("title", String(255)),
    Column("description", String(500)),
    Column("collection_name", String(255)),
    Column("level", String(255)),
    Column("created_by", String(100)),
    Column("is_deleted", Boolean, default=False),
    Column("updated_by", String(255), nullable=True),
    Column("created_at", TIMESTAMP, server_default=func.now()),
    Column("updated_at", TIMESTAMP, onupdate=func.now()),
]

for col in LEVEL_NAMES:
    topic_table_columns.append(Column(col, String(255), nullable=True))

content_table_columns = [
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("source", String(255)),
    Column("title", String(255)),
    Column("description", String(500)),
    Column("source_info", String(500), nullable=True),
    Column("source_data", String(500), nullable=True),
    Column("tags", String(255), nullable=True),
    Column("created_by", String(100)),
    Column("updated_by", String(255), nullable=True),
    Column("status", String(50), nullable=True),
    Column("version", String(50), nullable=True),
    Column("stored_in_kb", String(50), nullable=True),
    Column("topic_ids", ARRAY(Integer)),
    Column("is_deleted", Boolean, default=False),
    Column("created_at", TIMESTAMP, server_default=func.now()),
    Column("updated_at", TIMESTAMP, onupdate=func.now()),
    Column("review_date", TIMESTAMP),
    Column("approved_time", TIMESTAMP),
    Column("rejected_time", TIMESTAMP),
]

user_chat_history_columns = [
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("question", TEXT),
    Column("answer", TEXT),
    Column("model_name", String(255)),
    Column("topic_id", String(255)),
    Column("conversation_id", String(255)),
    Column("is_deleted", Boolean, default=False),
    Column("created_at", TIMESTAMP, server_default=func.now()),
    Column("updated_at", TIMESTAMP, onupdate=func.now()),
]

user_conversation_columns = [
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", TEXT),
    Column("username", String(255)),
    Column("created_at", TIMESTAMP, server_default=func.now()),
    Column("updated_at", TIMESTAMP, onupdate=func.now()),
]
