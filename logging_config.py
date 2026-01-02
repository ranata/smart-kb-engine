import time
from datetime import datetime as dt
import logging

from flask import Flask, request
from flask_restx import Api, Resource, fields

from logging_config import setup_logging

import configIA
import prompt_templates
import state_object
import vector_DB
import memoryMg
import retriever
import dbConnector


# ------------------------------------------------------------------
# Logging (ONE TIME)
# ------------------------------------------------------------------
setup_logging()
logger = logging.getLogger("ragBackend.flask_app")


# ------------------------------------------------------------------
# App startup (fail fast)
# ------------------------------------------------------------------
try:
    config = configIA.configure()

    connector = dbConnector.DBConnector()
    connector.connect()

    memory_store = memoryMg.MemoryStoreSQL(
        config.memory_vector_db_name,
        connector
    )
    memory_store.init_table()

    base_vector_cols = [
        "paragraph_category",
        "paragraph_pages",
        "paragraph_title",
        "paragraph_file",
        "paragraph_content",
        "Geo_Scope",
    ]

    knowledgeDB_doc = vector_DB.SQLvectorDB(
        config.base_vector_db_name,
        base_vector_cols,
        connector
    )
    knowledgeDB_doc.load_model()

    meta_data_cols = [
        "title",
        "file_name",
        "file_id",
        "summary",
        "category",
        "version_no",
        "Geo_Scope",
    ]

    knowledgeDB_meta = vector_DB.SQLvectorDB(
        config.meta_data_db_name,
        meta_data_cols,
        connector
    )
    knowledgeDB_meta.load_model()

    retriever_engine = retriever.RetrieverEng(
        knowledgeDB_doc,
        knowledgeDB_meta
    )

    process_engine = state_object.ProcessCollection(
        prompt_templates.process_system_prompts,
        prompt_templates.process_query_prompt_templates,
        retriever_engine,
    )

    state_context = {
        "process_engine": process_engine,
        "memory_store": memory_store,
        "knowledgeDB_meta": knowledgeDB_meta,
        "knowledgeDB_doc": knowledgeDB_doc,
    }

    state_machine = state_object.StateMachine(state_context)
    state_machine.build_graph()

except Exception:
    logger.exception("Fatal startup failure")
    raise


# ------------------------------------------------------------------
# Flask + API
# ------------------------------------------------------------------
app = Flask(__name__)
api = Api(
    app,
    version="1.0",
    title="IA LLM Backend",
    description="Intelligent Assistant API",
)


# ------------------------------------------------------------------
# API models
# ------------------------------------------------------------------
chat_info_model = api.model("ChatInfo", {
    "conversationId": fields.String(required=True),
    "interactionId": fields.String(required=True),
    "userId": fields.Integer(required=True),
    "userContext": fields.Raw(required=True),
    "userQuery": fields.String(required=True),
    "userQueryTime": fields.String(required=True),
    "firstInteraction": fields.Boolean(required=True),
})

llm_response_model = api.model("LLMResponse", {
    "type": fields.String,
    "data": fields.String,
    "responseTime": fields.String,
    "topicName": fields.String,
})

backend_response_model = api.model("BackendResponse", {
    "interactionId": fields.String,
    "conversationId": fields.String,
    "userId": fields.Integer,
    "userQuery": fields.String,
    "userQueryTime": fields.String,
    "llmResponse": fields.Nested(llm_response_model),
    "errorDetails": fields.Raw,
    "userContext": fields.Raw,
})


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def format_chat_output(state_response, chat_info):
    content = (
        state_response["chat"]
        if state_response["chat"]
        else state_response["default"]
    )

    response_type = "TEXT"
    error_details = {
        "code": state_response["health_code"],
        "message": "Success",
    }

    if state_response["health_code"].startswith("ERR"):
        response_type = "ERROR"
        error_details["message"] = content
    elif state_response["health_code"].startswith("WRN"):
        response_type = "WARNING"

    return {
        "interactionId": chat_info["interactionId"],
        "conversationId": chat_info["conversationId"],
        "userId": chat_info["userId"],
        "userQuery": chat_info["userQuery"],
        "userQueryTime": chat_info["userQueryTime"],
        "llmResponse": {
            "type": response_type,
            "data": content,
            "responseTime": dt.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "topicName": state_response.get("topic", ""),
        },
        "errorDetails": error_details,
        "userContext": chat_info["userContext"],
    }


def get_llm_response(chat_info):
    chatID = f"{chat_info['userId']}@{chat_info['conversationId']}"
    logger.info("Processing chatID=%s", chatID)

    state_message = {
        "chatID": chatID,
        "query": chat_info["userQuery"],
        "route": "start",
        "route_reason": "",
        "chat": "",
        "default": "",
        "country": "",
        "health_code": "",
        "check": "",
        "topic": "",
        "fetch_topic": "yes" if chat_info["firstInteraction"] else "no",
        "time_remain": config.time_out_thresh,
    }

    start = time.time()
    try:
        state_response = state_machine.invoke(state_message)
    except Exception:
        logger.exception("State machine failed | chatID=%s", chatID)
        raise

    logger.info(
        "LLM completed | chatID=%s | duration=%.3fs",
        chatID,
        time.time() - start,
    )

    return format_chat_output(state_response, chat_info)


# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------
@api.route("/api/v1/assistant/rag")
class RAGEndpoint(Resource):

    @api.expect(chat_info_model)
    @api.marshal_with(backend_response_model)
    def post(self):
        chat_info = request.json
        logger.debug(
            "Incoming request | interactionId=%s",
            chat_info.get("interactionId"),
        )
        return get_llm_response(chat_info)


@api.route("/health")
class LocalHealth(Resource):
    def get(self):
        return {"LLM_status_local": 200}


# ------------------------------------------------------------------
# Entrypoint
# ------------------------------------------------------------------
def main():
    logger.info("Starting IA LLM service")
    app.run(host="0.0.0.0", port=9090, threaded=True)


if __name__ == "__main__":
    main()
