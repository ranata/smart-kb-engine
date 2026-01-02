from typing import TypedDict
import time
from collections import defaultdict
import logging

from langgraph.graph import START, StateGraph, END

import tool_set
from llm_middleware import LLMChat


logger = logging.getLogger(__name__)


class ProcessCollection:
    def __init__(
        self,
        process_system_prompts,
        process_query_prompt_templates,
        retriever,
    ):
        self.chat_eng = LLMChat()
        self.retriever = retriever

        self.chatID_next_tool = defaultdict()
        self.chatID_current_query = defaultdict()
        self.chatID_response_msg = defaultdict()
        self.chatID_response_msg_for_consol = defaultdict()

        self.process_system_prompts = process_system_prompts
        self.process_query_prompt_templates = process_query_prompt_templates

    def chat(
        self,
        query,
        chatID,
        memory_store,
        fetch_topic="yes",
        channel="router",
        filter_rag1="",
        time_limit=48,
    ):
        status_msg_chat = []
        topic_title = ""

        start_time = time.time()
        timeout_msg = (
            "We didn't get a response due to a technical issue. "
            "Please try again later."
        )

        logger.info(
            "ProcessCollection.chat | channel=%s | chatID=%s",
            channel,
            chatID,
        )

        # --------------------------------------------------
        # ROUTER
        # --------------------------------------------------
        if channel == "router":
            response_message, status_msg = self.chat_eng.get_router_response(
                query=query,
                memory_store=memory_store,
                chatID=chatID,
                system_prompt=self.process_system_prompts[channel],
            )

            status_msg_chat.append(status_msg)

            if status_msg != "OK000":
                return response_message, status_msg_chat, topic_title

        # --------------------------------------------------
        # RAG
        # --------------------------------------------------
        elif channel == "RAG":
            context, file_hits = self.retriever.retrieve_for_RAG(
                query,
                filter_cont=filter_rag1,
            )

            if not file_hits:
                status_msg_chat.append("ERR003")
                return (
                    {"role": "assistant", "content": "No relevant context found."},
                    status_msg_chat,
                    topic_title,
                )

            aug_query = self.chat_eng.augment(
                query,
                context,
                self.process_query_prompt_templates[channel],
            )

            response_message, status_msg, topic_title = (
                self.chat_eng.get_RAG_response(
                    query=query,
                    aug_query=aug_query,
                    memory_store=memory_store,
                    chatID=chatID,
                    system_prompt=self.process_system_prompts[channel],
                    topic_system_prompt=self.process_system_prompts["topic"],
                    fetch_topic=fetch_topic,
                )
            )

            status_msg_chat.append(status_msg)

            if status_msg != "OK001":
                return response_message, status_msg_chat, topic_title

        # --------------------------------------------------
        # NON-RAG
        # --------------------------------------------------
        elif channel == "non_RAG":
            response_message, status_msg, topic_title = (
                self.chat_eng.non_RAG_response(
                    query=query,
                    memory_store=memory_store,
                    chatID=chatID,
                    system_prompt=self.process_system_prompts[channel],
                    query_prompt_template=self.process_query_prompt_templates[channel],
                    topic_system_prompt=self.process_system_prompts["topic"],
                )
            )

            status_msg_chat.append(status_msg)

            if status_msg != "OK001":
                return response_message, status_msg_chat, topic_title

        # --------------------------------------------------
        # INVALID CHANNEL
        # --------------------------------------------------
        else:
            status_msg_chat.append("ERR004")
            return (
                {
                    "role": "assistant",
                    "content": f"Invalid channel: {channel}",
                },
                status_msg_chat,
                topic_title,
            )

        # --------------------------------------------------
        # TIMEOUT CHECK
        # --------------------------------------------------
        elapsed = time.time() - start_time
        if time_limit - elapsed <= 0:
            status_msg_chat.append("ERR005")
            logger.warning(
                "Timeout | channel=%s | elapsed=%.2f",
                channel,
                elapsed,
            )
            return (
                {"role": "assistant", "content": timeout_msg},
                status_msg_chat,
                topic_title,
            )

        self.chatID_response_msg[chatID] = response_message
        self.chatID_response_msg_for_consol[chatID] = f"{channel}: {response_message}"

        return response_message, status_msg_chat, topic_title
