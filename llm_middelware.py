import logging
from datetime import datetime as dt
from typing import List, Tuple, Optional

from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    AIMessage,
)

from aif_chat_model import AIFChatModel
from guardrail_utils import mask_pii_preserve_country

logger = logging.getLogger(__name__)


class LLMChat:
    """
    LangChain-native LLM interaction layer.
    No HTTP, no payload construction, no response parsing.
    """

    def __init__(self):
        self.llm = AIFChatModel()
        logger.info("LLMChat initialized with AIFChatModel")

    # ------------------------------------------------------------------
    # Core execution wrapper
    # ------------------------------------------------------------------
    def _invoke_llm(
        self,
        *,
        messages: List,
        channel: str,
        chatID: str,
    ) -> AIMessage:
        """
        Centralized LLM invocation with logging and error handling
        """
        try:
            logger.info(
                "Invoking LLM | channel=%s | chatID=%s | messages=%d",
                channel,
                chatID,
                len(messages),
            )

            logger.debug(
                "LLM messages | channel=%s | chatID=%s | %s",
                channel,
                chatID,
                messages,
            )

            response: AIMessage = self.llm.invoke(messages)

            logger.info(
                "LLM response received | channel=%s | chatID=%s",
                channel,
                chatID,
            )

            logger.debug(
                "LLM response content | channel=%s | chatID=%s | %s",
                channel,
                chatID,
                response.content,
            )

            return response

        except Exception:
            logger.exception(
                "LLM invocation failed | channel=%s | chatID=%s",
                channel,
                chatID,
            )
            raise

    # ------------------------------------------------------------------
    # Router response
    # ------------------------------------------------------------------
    def get_router_response(
        self,
        query: str,
        memory_store,
        chatID: str,
        process_system_prompt: List[SystemMessage],
    ) -> Tuple[AIMessage, str]:

        channel = "router"
        logger.info("Router processing started | chatID=%s", chatID)

        user_msg = HumanMessage(
            content=mask_pii_preserve_country(query)
        )

        messages = process_system_prompt + [user_msg]

        try:
            ai_msg = self._invoke_llm(
                messages=messages,
                channel=channel,
                chatID=chatID,
            )
            status_msg = "OK000"

        except Exception:
            ai_msg = AIMessage(
                content="Unable to process your request at the moment. Please try again."
            )
            status_msg = "ERR001"

        self._persist_conversation(
            memory_store,
            chatID,
            channel,
            user_msg,
            ai_msg,
        )

        return ai_msg, status_msg

    # ------------------------------------------------------------------
    # RAG response
    # ------------------------------------------------------------------
    def get_RAG_response(
        self,
        query: str,
        aug_query: str,
        memory_store,
        chatID: str,
        process_system_prompt: List[SystemMessage],
        topic_system_prompt: List[SystemMessage],
        fetch_topic: str = "yes",
    ) -> Tuple[AIMessage, str, str]:

        channel = "RAG"
        logger.info("RAG processing started | chatID=%s", chatID)

        user_msg = HumanMessage(
            content=mask_pii_preserve_country(aug_query)
        )

        messages = process_system_prompt + topic_system_prompt + [user_msg]

        try:
            ai_msg = self._invoke_llm(
                messages=messages,
                channel=channel,
                chatID=chatID,
            )
            status_msg = "OK001"

        except Exception:
            ai_msg = AIMessage(
                content="Unable to process your request at the moment. Please try again."
            )
            status_msg = "ERR001"

        topic_title = (
            self._get_topic_title(
                memory_store,
                chatID,
                topic_system_prompt,
                ai_msg.content,
            )
            if fetch_topic == "yes"
            else ""
        )

        self._persist_conversation(
            memory_store,
            chatID,
            channel,
            user_msg,
            ai_msg,
            topic_title,
        )

        return ai_msg, status_msg, topic_title

    # ------------------------------------------------------------------
    # Non-RAG response
    # ------------------------------------------------------------------
    def non_RAG_response(
        self,
        query: str,
        memory_store,
        chatID: str,
        process_system_prompt: List[SystemMessage],
        query_prompt_template: List[SystemMessage],
        topic_system_prompt: List[SystemMessage],
    ) -> Tuple[AIMessage, str, str]:

        channel = "non_RAG"
        logger.info("Non-RAG processing started | chatID=%s", chatID)

        user_msg = HumanMessage(
            content=mask_pii_preserve_country(query)
        )

        messages = process_system_prompt + query_prompt_template + [user_msg]

        try:
            ai_msg = self._invoke_llm(
                messages=messages,
                channel=channel,
                chatID=chatID,
            )
            status_msg = "OK001"

        except Exception:
            ai_msg = AIMessage(
                content="Unable to process your request at the moment. Please try again."
            )
            status_msg = "ERR001"

        topic_title = self._get_topic_title(
            memory_store,
            chatID,
            topic_system_prompt,
            ai_msg.content,
        )

        self._persist_conversation(
            memory_store,
            chatID,
            channel,
            user_msg,
            ai_msg,
            topic_title,
        )

        return ai_msg, status_msg, topic_title

    # ------------------------------------------------------------------
    # Topic extraction
    # ------------------------------------------------------------------
    def _get_topic_title(
        self,
        memory_store,
        chatID: str,
        topic_system_prompt: List[SystemMessage],
        content: str,
    ) -> str:

        try:
            logger.debug("Generating topic title | chatID=%s", chatID)

            response = self.llm.invoke(
                topic_system_prompt + [HumanMessage(content=content)]
            )

            topic = response.content.strip()
            logger.info("Topic generated | chatID=%s | topic=%s", chatID, topic)
            return topic

        except Exception:
            logger.exception("Topic generation failed | chatID=%s", chatID)
            return f"Topic_auto_{dt.utcnow().strftime('%Y%m%d_%H%M%S')}"

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def _persist_conversation(
        self,
        memory_store,
        chatID: str,
        channel: str,
        user_msg: HumanMessage,
        ai_msg: AIMessage,
        topic: str = "",
    ):
        try:
            memory_store.add_sql(
                [
                    {
                        "role": "user",
                        "content": user_msg.content,
                        "channel": channel,
                        "chatID": chatID,
                        "timestamp": dt.utcnow(),
                        "topic": topic,
                    },
                    {
                        "role": "assistant",
                        "content": ai_msg.content,
                        "channel": channel,
                        "chatID": chatID,
                        "timestamp": dt.utcnow(),
                        "topic": topic,
                    },
                ]
            )
            logger.debug(
                "Conversation persisted | chatID=%s | channel=%s",
                chatID,
                channel,
            )

        except Exception:
            logger.exception(
                "Failed to persist conversation | chatID=%s | channel=%s",
                chatID,
                channel,
            )
