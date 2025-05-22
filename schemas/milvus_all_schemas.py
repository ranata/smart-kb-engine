from pymilvus import FieldSchema, DataType

mv_content_fields = [
    FieldSchema(
        name="id", dtype=DataType.INT64, max_length=50, is_primary=True, auto_id=True
    ),
    FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=20000),
    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=1536),
    FieldSchema(name="summary", dtype=DataType.VARCHAR, max_length=500),
    FieldSchema(name="topics", dtype=DataType.JSON, max_length=500),
    FieldSchema(name="questions", dtype=DataType.JSON, max_length=1000),
    FieldSchema(name="named_entities", dtype=DataType.JSON, max_length=500),
    FieldSchema(name="metadata", dtype=DataType.JSON, max_length=5000),
    FieldSchema(name="topic_ids", dtype=DataType.JSON, max_length=500),
    FieldSchema(name="content_id", dtype=DataType.VARCHAR, max_length=200),
    FieldSchema(name="is_deleted", dtype=DataType.BOOL, max_length=200),
]
