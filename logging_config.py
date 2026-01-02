import logging
import time
from datetime import datetime as dt

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

from get_token import get_token_from_sc_idp
from sc_idp_token_enc import decrypt_sc_idp_token

import requests

# ------------------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------------------
logger = setup_logging()  # returns ragBackend logger

# ------------------------------------------------------------------------------
# App startup (FAIL FAST)
# ------------------------------------------------------------------------------
try:
    config = configIA.configure()

    connector = dbConnector.DBConnector()
    connector.connect()

    memory_store = memoryMg.MemoryStoreSQL(
        config.memory_vector_db_name, connector
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
        config.base_vector_db_name, base_vector_cols, connector
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
        config.meta_data_db_name, meta_data_cols, connector
    )
    knowledgeDB_meta.load_model()

    retriever_engine = retriever.RetrieverEng(
        knowledgeDB_doc, knowledgeDB_meta
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

# ------------------------------------------------------------------------------
# Flask / API
# ------------------------------------------------------------------------------
app = Flask(__name__)
api = Api(
    app,
    version="1.0",
    title="IA LLM Backend",
    description="Intelligent Assistant API service",
)

# ------------------------------------------------------------------------------
# API Models
# ------------------------------------------------------------------------------
chat_info_model = api.model(
    "ChatInfo",
    {
        "conversationId": fields.String(required=True),
        "interactionId": fields.String(required=True),
        "userId": fields.Integer(required=True),
        "userQuery": fields.String(required=True),
        "userQueryTime": fields.String(required=True),
        "firstInteraction": fields.Boolean(required=True),
        "userContext": fields.Raw(required=True),
    },
)

llm_response_model = api.model(
    "LLMResponse",
    {
        "type": fields.String,
        "data": fields.String,
        "responseTime": fields.String,
        "topicName": fields.String,
    },
)

backend_response_model = api.model(
    "BackendResponse",
    {
        "interactionId": fields.String,
        "conversationId": fields.String,
        "userId": fields.Integer,
        "userQuery": fields.String,
        "userQueryTime": fields.String,
        "llmResponse": fields.Nested(llm_response_model),
        "errorDetails": fields.Raw,
        "userContext": fields.Raw,
    },
)

# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------
def format_chat_output(state, chat_info):
    response_type = "TEXT"
    content = state["chat"] or state["default"]

    if state["health_code"].startswith("ERR"):
        response_type = "ERROR"
    elif state["health_code"].startswith("WRN"):
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
            "topicName": state.get("topic", ""),
        },
        "errorDetails": {
            "code": state["health_code"],
            "message": "Success" if not state["health_code"].startswith("ERR") else content,
        },
        "userContext": chat_info["userContext"],
    }


def get_llm_response(chat_info):
    chatID = f"{chat_info['userId']}@{chat_info['conversationId']}"
    logger.info("Processing chatID=%s", chatID)

    state = {
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
        result = state_machine.invoke(state)
    except Exception:
        logger.exception("State machine failed | chatID=%s", chatID)
        raise

    logger.info(
        "LLM completed | chatID=%s | duration=%.3fs",
        chatID,
        time.time() - start,
    )

    return format_chat_output(result, chat_info)

# ------------------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------------------
@api.route("/api/v1/assistant/rag")
class RAG(Resource):
    @api.expect(chat_info_model)
    @api.marshal_with(backend_response_model)
    def post(self):
        chat_info = request.json
        logger.debug("Incoming request | interactionId=%s", chat_info["interactionId"])
        return get_llm_response(chat_info)


@api.route("/api/v1/health-check")
class HealthCheck(Resource):
    def get(self):
        try:
            token = decrypt_sc_idp_token()
        except FileNotFoundError:
            token = get_token_from_sc_idp()

        headers = {"Authorization": f"Bearer {token}"}
        url = config.url_dict[config.LLM_model_name]

        try:
            r = requests.post(
                url,
                headers=headers,
                json={"messages": [{"role": "user", "content": "ping"}]},
                timeout=5,
                verify=False,
            )
        except Exception:
            logger.exception("Health check HTTP failure")
            return {"LLM_BK_status": "DOWN"}, 503

        return {"LLM_BK_status": f"UP ({r.status_code})"}

@api.route("/health")
class LocalHealth(Resource):
    def get(self):
        return {"LLM_status_local": 200}

# ------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------
def main():
    logger.info("Starting IA LLM service")
    app.run(host="0.0.0.0", port=9090, threaded=True)


if __name__ == "__main__":
    main()
