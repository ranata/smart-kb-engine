from pydantic import Field
from config.constants import LEVEL_NAMES

# add topic fields
add_topic_fields = {
    "title": (str, Field(...)),
    "description": (str, Field(...)),
    "level": (str, Field(...)),
    "created_by": (str, Field(...)),
    "prompt_id": (str, Field(default="")),
}

for field_name in LEVEL_NAMES:
    add_topic_fields[field_name] = (str, Field(default=""))

# edit topic fields
edit_topic_fields = {
    "id": (str, Field(...)),
    "title": (str, Field(...)),
    "description": (str, Field(...)),
    "level": (str, Field(...)),
    "updated_by": (str, Field(...)),
    "prompt_id": (str, Field(default="")),
}

for field_name in LEVEL_NAMES:
    edit_topic_fields[field_name] = (str, Field(default=""))

# get topic fields
get_topic_fields = {
    "is_all": (bool, Field("")),
}
for field_name in LEVEL_NAMES:
    get_topic_fields[field_name] = (str, Field(default=""))


# content scrape fields
content_scrape_fields = {
    "url": (str, Field(...)),
    "type": (str, Field(...)),
    "username": (str, Field(...)),
    "key_name": (str, Field("")),
    "token": (str, Field("")),
}

# create content fields
create_content_fields = {
    "title": (str, Field(...)),
    "description": (str, Field(...)),
    "source": (str, Field("")),
    "source_info": (str, Field(...)),
    "source_data": (str, Field("")),
    "tags": (str, Field(...)),
    "created_by": (str, Field(...)),
    "version": (str, Field("")),
    "topic_ids": (str, Field(...)),
    "level": (str, Field(...)),
    "key_name": (str, Field("")),
    "username": (str, Field(...)),
}

# edit content fields
edit_content_fields = {
    "id": (str, Field(...)),
    "title": (str, Field(...)),
    "description": (str, Field(...)),
    "tags": (str, Field(...)),
    "version": (str, Field("")),
    "topic_ids": (str, Field(...)),
    "status": (str, Field(...)),
    "updated_by": (str, Field(...)),
}


# get content fields
get_content_fields = {}
for field_name in LEVEL_NAMES:
    get_content_fields[field_name] = (str, Field(default=""))

parse_content_fields = {
    "content_id": (str, Field(...)),
    "url": (str, Field("")),
    "page_no": (str, Field("")),
}

search_knowledge_base_fields = {
    "search_key": (str, Field(...)),
    "username": (str, Field(...)),
    "con_id": (str, Field("")),
    "topic_id": (str, Field("")),
    "l2": (str, Field("")),
    "l3": (str, Field("")),
}

list_chat_threads_fields = {
    "username": (str, Field(...)),
}
