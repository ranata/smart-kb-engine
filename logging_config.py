from typing import TypedDict
import time
from collections import defaultdict
from langgraph.graph import START, StateGraph, MessagesState, END

import tool_set
import LLM_Response


class ProcessCollection:
    def __init__(self, 
                 process_system_prompts, 
                 process_query_prompt_templates,
                 retriever
                 ):

        self.chat_eng = LLM_Response.LLMChat()
        self.retriever = retriever
        self.chatID_next_tool = defaultdict()
        self.chatID_current_query = defaultdict()
        self.chatID_response_msg = defaultdict()
        self.chatID_response_msg_for_consol = defaultdict()
        self.process_system_prompts = process_system_prompts
        self.process_query_prompt_templates = process_query_prompt_templates

    def chat(self, 
             query, 
             chatID, 
             memory_store, 
             fetch_topic = 'yes',
             channel = "router", 
             filter_rag1 = "",
             time_limit = 48
             ):
        status_msg_chat = []
        query_prompt_template = self.process_query_prompt_templates[channel]
        process_system_prompt = self.process_system_prompts[channel]
        topic_system_prompt = self.process_system_prompts["topic"]
        topic_title = ""

        time_out_message = "We didn't get a response. This could be due to a technical issue or a guideline concern. Please try again, or log an incident if the issue continues."
        start_time = time.time()
        if channel == "router":
            response_message, status_msg = self.chat_eng.get_router_response(query, memory_store, 
                                                          chatID, process_system_prompt)
            # time.sleep(47)
            elapsed = time.time() - start_time
            if time_limit - elapsed < 3:
                status_msg_chat.append("ERR005")
            status_msg_chat.append(status_msg)
            if status_msg != "OK000":
                return response_message, status_msg_chat, topic_title
            
        elif channel  == "RAG":
            context, file_hits = self.retriever.retrieve_for_RAG(query, filter_cont=filter_rag1)
            if len(file_hits) == 0:
                status_msg_chat.append("ERR003")
                response_message = {"role": "assistant",  "content": "We're having trouble retrieving the necessary information right now. Please try again later."}
                return response_message, status_msg_chat, topic_title
            # time.sleep(47)
            elapsed = time.time() - start_time
            if time_limit - elapsed < 3:
                status_msg_chat.append("ERR005")
                print(f"!!! retirever timeout: expected {time_limit}, task time: {elapsed}")
                response_message = {"role": "assistant",  "content": time_out_message}
                return response_message, status_msg_chat, topic_title
            
            aug_query = self.chat_eng.augment(query, context, query_prompt_template)
            response_message, status_msg, topic_title = self.chat_eng.get_RAG_response(query, 
                                                                          aug_query, 
                                                                          memory_store, 
                                                                          chatID, 
                                                                          process_system_prompt, 
                                                                          topic_system_prompt,
                                                                          fetch_topic = fetch_topic)
            status_msg_chat.append(status_msg)
            # time.sleep(47)
            elapsed = time.time() - start_time
            if time_limit - elapsed < 0:
                status_msg_chat.append("ERR005")
                print(f"!!! RAG_AI timeout: expected {time_limit}, task time: {elapsed}")
                response_message = {"role": "assistant",  "content": time_out_message}
                return response_message, status_msg_chat, topic_title
            if status_msg != "OK001":
                return response_message, status_msg_chat, topic_title
            
        elif channel == "non_RAG":
            query_prompt_template = self.process_query_prompt_templates[channel]
            response_message, status_msg, topic_title = self.chat_eng.non_RAG_response(query, 
                                                                          memory_store, 
                                                                          chatID, 
                                                                          process_system_prompt, 
                                                                          query_prompt_template,
                                                                          topic_system_prompt
                                                                          )
            status_msg_chat.append(status_msg)
            # time.sleep(47)
            elapsed = time.time() - start_time
            if time_limit - elapsed < 0:
                status_msg_chat.append("ERR005")
                print(f"!!! non_RAG timeout: expected {time_limit}, task time: {elapsed}")
                response_message = {"role": "assistant",  "content": time_out_message}
                return response_message, status_msg_chat, topic_title
            if status_msg != "OK001":
                return response_message, status_msg_chat, topic_title
        else:
            status_msg_chat.append('ERR004')
            response_message = {"role": "assistant",  "content": f"The channel should be among [RAG, router, non_RAG] found: {channel}"}
            return response_message, status_msg_chat, topic_title

        self.chatID_response_msg[chatID] = response_message
        self.chatID_response_msg_for_consol[chatID] = f"{channel}: {response_message}"

        return response_message, status_msg_chat, topic_title


#######################################
    
    
class State(TypedDict):
    query: str
    chatID: str
    route: str
    route_reason: str
    chat: str
    country: str
    default: str
    check: str
    health_code: str
    fetch_topic: str
    topic: str
    time_remain: float

        
class StateMachine():
    def __init__(self, state_context):
        self.tool_kit = tool_set.ToolKit(state_context)
        self.workflow = StateGraph(State)
        self.state_graph = None
        self.graph_shap = None
        
    def _check_route(self, state_message):
        next_tool = state_message['route']
        allowed_route = ["RAG_processing", "response_default", "non_RAG"]
        if next_tool in allowed_route:
            return next_tool
        else:
            return "END"
        
        
    def build_graph(self):
        self.workflow.add_node("router", self.tool_kit.router)
        self.workflow.add_node("RAG_processing", self.tool_kit.RAG_processing)
        self.workflow.add_node("non_RAG", self.tool_kit.non_RAG_processing)
        self.workflow.add_node("response_default", self.tool_kit.response_default)
        self.workflow.add_node("guardrail_internal", self.tool_kit.guardrail_internal)
        
        self.workflow.add_edge(START, 'router')
        
        route_mapping = {"RAG_processing": "RAG_processing", 
                         "response_default": "response_default",
                         "non_RAG": "non_RAG",
                         "END": END
                        }
        self.workflow.add_conditional_edges('router', self._check_route, route_mapping)
        
        self.workflow.add_edge('RAG_processing', 'guardrail_internal')
        self.workflow.add_edge('non_RAG', 'guardrail_internal')
        self.workflow.add_edge('guardrail_internal', END)
 
        self.state_graph = self.workflow.compile()
        self.graph_shap = self.state_graph.get_graph().draw_ascii()

    def invoke(self, state):
        state_response = self.state_graph.invoke(state)
        return state_response
    
