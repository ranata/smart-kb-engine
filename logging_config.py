import logging
from logging_config import setup_logging

import os
import pandas as pd
import json
import requests
import time
from collections import defaultdict
from datetime import datetime as dt


from langgraph.graph import START, StateGraph, MessagesState, END

from flask import Flask, request, jsonify
from flask_restx import Api, Resource, fields

import configIA
import prompt_templates
import state_object
import vector_DB
import memoryMg
import retriever
import dbConnector
from get_token import get_token_from_sc_idp
from sc_idp_token_enc import decrypt_sc_idp_token

setup_logging()

logger = logging.getLogger(__name__)

### configure
try:
    config = configIA.configure()
    connector = dbConnector.DBConnector()
    connector.connect()
except Exception as e:
    logger.exception("Failed during application startup (config / DB connection)")
    raise

### resource

memory_store = memoryMg.MemoryStoreSQL(config.memory_vector_db_name, connector)
memory_store.init_table()

try:
    base_vector_cols =  ['paragraph_category', 
                    'paragraph_pages', 
                    'paragraph_title', 
                    'paragraph_file', 
                    'paragraph_content',
                    'Geo_Scope'
                    ]

    knowledgeDB_doc = vector_DB.SQLvectorDB(config.base_vector_db_name, base_vector_cols, connector)
    knowledgeDB_doc.load_model()

    meta_data_cols =  ['title', 'file_name', 'file_id', 'summary', 'category', 'version_no', 'Geo_Scope']
    knowledgeDB_meta = vector_DB.SQLvectorDB(config.meta_data_db_name, meta_data_cols, connector)
    knowledgeDB_meta.load_model()

except Exception as e:
    logger.exception("Failed while loading vector DB models")
    raise


retriever_engine = retriever.RetrieverEng(knowledgeDB_doc,  knowledgeDB_meta)

process_engine = state_object.ProcessCollection(prompt_templates.process_system_prompts, 
                                                prompt_templates.process_query_prompt_templates,
                                                retriever_engine
                                            )


### workflow

state_context = {"process_engine": process_engine, 
                 "memory_store": memory_store, 
                 "knowledgeDB_meta": knowledgeDB_meta, 
                 "knowledgeDB_doc": knowledgeDB_doc
                }
# state_context

try:
    state_machine = state_object.StateMachine(state_context)
    state_machine.build_graph()

except Exception as e:
    logger.exception("Failed while building state machine graph")
    raise


### App

app = Flask(__name__)
api = Api(app, version='1.0', title='IA LLM Backend', description='Intelligent Assistant API service')

############### data model

chat_info_model = api.model('ChatInfo', {
    'conversationId': fields.String(required=True),
    'interactionId': fields.String(required=True),
    'userId': fields.Integer(required=True),
    'userContext': fields.Nested(api.model('UserContext', {
        'entityId': fields.String(required=True),
        'entityType': fields.String(required=True),
        'country': fields.String(required=True),
        'screenHeader': fields.String(required=True),
        'tabName': fields.String(required=True),
        'documentId': fields.String(required=True)
    }), required=True),
    'userQuery': fields.String(required=True),
    'userQueryTime': fields.String(required=True),
    'firstInteraction': fields.Boolean(required=True)
}) #-------


llm_response_model = api.model('LLMResponse', {
    'type': fields.String(required=True),
    'data': fields.String(required=True),
    'responseTime': fields.String(required=True),
    'topicName': fields.String(required=True)
}) #-------

error_detail_response_model = api.model('errorDetails', {
    'code': fields.String(required=True),
    'message': fields.String(required=True)
}) #-------

user_context_model = api.model('UserContext', {
    'entityId': fields.String(required=True),
    'entityType': fields.String(required=True),
    'country': fields.String(required=True),
    'screenHeader': fields.String(required=True),
    'tabName': fields.String(required=True),
    'documentId': fields.String(required=True)
}) #-------

backend_response_model = api.model('BackendResponse', {
    'interactionId': fields.String(required=True),
    'conversationId': fields.String(required=True),
    'userId': fields.Integer(required=True),
    'userQuery': fields.String(required=True),
    'userQueryTime': fields.String(required=True),
    'llmResponse': fields.Nested(llm_response_model),
    'errorDetails': fields.Nested(error_detail_response_model, allow_null=True),
    'userContext': fields.Nested(user_context_model, required=True)
}) #-------

echo_health_model = api.model('EchoHealth', {
    'LLM_BK_status': fields.String(required=True)
})

echo_local_health_model = api.model('EchoHealthLocal', {
    'LLM_status_local': fields.Integer(required=True)
})

############### LLM backend response related

def format_chat_output(state_response, 
                       interactionId, 
                       session_id, 
                       user_id,       
                       query, 
                       userQueryTime, 
                       userContext):
    return_info = {}
    llm_resp_content = state_response["chat"] if len(state_response["chat"]) > 0 else state_response["default"]

    err_msg = {"code": state_response['health_code'], "message": "Success"}
    llm_rps_data = llm_resp_content

    if "ERR006" in state_response['health_code']:
        response_type = "CONTENT_SAFETY_TRIGGERED"
        err_msg["message"] = llm_resp_content
        llm_rps_data = llm_resp_content
    elif "ERR003" in state_response['health_code']:
        response_type = "NO_CONTEXT"
        err_msg["message"] = llm_resp_content
        llm_rps_data = llm_resp_content
    elif state_response['route_reason'] == 'not english':
        response_type = "NON_ENGLISH"
        err_msg["message"] = llm_resp_content
        llm_rps_data = llm_resp_content
    elif "ERR007" in state_response['health_code']:
        response_type = "PROMPT_SHORT"
        err_msg["message"] = llm_resp_content
        llm_rps_data = llm_resp_content
    elif "ERR" in state_response['health_code']:
        response_type = "ERROR"
        err_msg["message"] = llm_resp_content
        llm_rps_data = llm_resp_content
    elif "WRN" in state_response['health_code']:
        response_type = "WARNNING"
        err_msg["message"] = llm_resp_content
        llm_rps_data = llm_resp_content
    else:
        response_type = "TEXT"


    llm_rps = {"type": response_type,
               'data': llm_rps_data,
               'responseTime': dt.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
               'topicName': state_response['topic']
               }
    return_info["errorDetails"] = err_msg.copy()
    return_info["interactionId"] = interactionId
    return_info["conversationId"] = session_id
    return_info["userId"] = user_id
    return_info['userQuery'] = query 
    return_info["userQueryTime"] = userQueryTime
    return_info['llmResponse'] = llm_rps.copy()
    return_info["userContext"] = userContext.copy()
    return return_info

def get_llm_response(chat_info):
    global state_machine
    global config
    chatID = "@".join([str(chat_info['userId']), chat_info['conversationId']])
    logger.info("Processing chatID=%s", chatID)
    query = chat_info['userQuery']
    
    fetch_topic = "yes" if (chat_info["firstInteraction"]) else "no"

    logger.debug(
        "fetch_topic=%s firstInteraction=%s type=%s",
        fetch_topic,
        chat_info["firstInteraction"],
        type(chat_info["firstInteraction"])
    )
    
    state_message: state_object.State = {"chatID": chatID, 
                                         "query": query,
                                         "route": "start",
                                         "route_reason": "",
                                         "chat": "",
                                         "default": "",
                                         "country": "",
                                         "health_code": "",
                                         "check": '',
                                         "topic": "",
                                         "fetch_topic": fetch_topic,
                                         "time_remain": config.time_out_thresh
                                        }
    
    start_time = time.time()
    try:
        state_response = state_machine.invoke(state_message)
    except Exception as e:
        logger.exception(
            "State machine invocation failed | chatID=%s | query=%s",
            chatID,
            query
        )
        raise

    
    end_time = time.time()

    logger.info(
        "LLM call duration=%.3f seconds",
        end_time - start_time
    )
    
    response_msg = format_chat_output(state_response, 
                                      chat_info["interactionId"], 
                                      chat_info["conversationId"],
                                      chat_info["userId"], 
                                      chat_info['userQuery'],
                                      chat_info['userQueryTime'],
                                      chat_info["userContext"]
                                      )
    
    return response_msg

############### LLM backend
@api.route('/api/v1/assistant/rag') #/llmResponse
class ProcessUserInfo(Resource):
    @api.expect(chat_info_model)
    @api.marshal_with(backend_response_model)
    def post(self):
        chat_info = request.json
        logger.debug("Incoming chat_info=%s", chat_info)
        return get_llm_response(chat_info)

############### Health check
@api.route('/api/v1/health-check')
class HealthCheck_backend_test(Resource):
    @api.marshal_with(echo_health_model)
    def get(self):
        config = configIA.configure()
        # define data payload

        data_payload = {"model": config.LLM_model_name,
                        "messages": [{"role": "system",
                                      "content": "You are a helpful assistant to echo the user for connectivity verification"},
                                     {"role": "user",
                                      "content": "please echo"}
                                     ],
                        "temperature": 0.01,
                        "guardrails": ["custom-guardrails", "content-safety"]
                        }
        # define the url
        model = data_payload["model"]
        url = config.url_dict[model]

        # Check if token exists else get it and save
        try:
            access_token = decrypt_sc_idp_token()
        except FileNotFoundError:
            logger.info("Encrypted token not found, fetching new token from IDP")
            access_token = get_token_from_sc_idp()
        except Exception as e:
            logger.exception("Unexpected wrror while decrypting access token")
            raise
        # To remove if token encryption is working
        # if "sc_idp_token.txt" in os.listdir():
        #     with open("sc_idp_token.txt", "r") as f:
        #         access_token = f.read()
        # else:
        #     access_token = get_token_from_sc_idp()

        # Define headers
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'text/plain'
        }

        # Ping the LLM endpoint to check
        try:
            response = requests.request("POST", url, headers=headers, json=data_payload, timeout=config.time_out_thresh, verify=False)
        except Exception as e:
            logger.exception(
                "LLM HTTP request failed | url=%s | timeout=%s",
                url,
                config.time_out_thresh
            )
            raise

        if response.status_code in [200]:
            status = f"Remote LLM service returned status code: {response.status_code}"
        else:
            retry_count = 0
            while response.status_code != 200 and retry_count < config.llm_retries:
                logger.warning(
                    "LLM returned status=%s | retry=%s/%s",
                    response.status_code,
                    retry_count + 1,
                    config.llm_retries
                )

                if response.status_code in [401]:  # Invalid or Expired Token
                    access_token = get_token_from_sc_idp()
                    logger.info("New access token obtained from IDP")
                    headers['Authorization'] = f'Bearer {access_token}'
                
                response = requests.request("POST", url, headers=headers, json=data_payload, timeout=config.time_out_thresh, verify=False)
                retry_count += 1
                time.sleep(1)
            if response.status_code in [200]:
                status = f"Remote LLM service returned status code: {response.status_code}"
            else:
                status = f"Remote LLM service is NOT healthy, status code: {response.status_code}"
        response = {"LLM_BK_status": status}
        return response

#### local API basic healthiness
@api.route('/health')
class BasicHealthCheck(Resource):
    @api.marshal_with(echo_local_health_model)
    def get(self):
        response = {"LLM_status_local": 200}
        return response

############### main
def main():
    app.run(host="0.0.0.0", port=9090, threaded=True) #, threaded=True
    # app.run(host='0.0.0.0', port=443, ssl_context=(config.cert_path, config.key_path))

    
############### Gateway
if __name__ == "__main__":
    main()
