import logging
import time
import requests
from typing import List, Optional, Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.callbacks import CallbackManagerForLLMRun
from pydantic import Field, PrivateAttr

import configIA
from get_token import get_token_from_sc_idp
from sc_idp_token_enc import decrypt_sc_idp_token

logger = logging.getLogger(__name__)

class AIFChatModel(BaseChatModel):
    """
    LangChain-compatible ChatModel that wraps
    JWT-based AI Factory LLM endpoint
    """

    config: Any = Field(default=None, exclude=True)
    _access_token: Optional[str] = PrivateAttr(default=None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.config = configIA.configure()
        self._access_token: Optional[str] = None

    @property
    def _llm_type(self) -> str:
        return "aif-chat-model"

    def _get_token(self) -> str:
        try:
            return decrypt_sc_idp_token()
        except FileNotFoundError:
            return get_token_from_sc_idp()
        
    def _headers(self) -> dict:
        if not self._access_token:
            self._access_token = self._get_token()

        return {
            "Authorization": f"Bearer {self._access_token}",
            "content-Type": "application/json",
        }
        

    def _to_payload_messages(self, messages: List[BaseMessage]) -> list:
        payload_msgs = []
        for m in messages:
            role = "user"
            if m.type == "system":
                role = "system"
            elif m.type == "ai":
                role = "assistant"

            payload_msgs.append(
                {
                    "role": role,
                    "content": m.content,
                }
            )
        return payload_msgs

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        **kwargs,
    ) -> ChatResult:
        payload = {
            "model": self.config.LLM_model_name,
            "messages": self._to_payload_messages(messages),
            "temperature": kwargs.get("temperature", 0.01),
            "guardrails": ["custom-guardrails", "content-safety"],
        }

        url = self.config.url_dict[self.config.LLM_model_name]

        for attempt in range(self.config.llm_retries):
            response = requests.post(
                url,
                headers=self._headers(),
                json=payload,
                timeout=self.config.time_out_thresh,
                verify=False
            )

            if response.status_code == 401:
                self._access_token = get_token_from_sc_idp()
                continue

            if response.status_code != 200:
                logger.error(
                    "AIFChatModel call failed | status=%s | body=%s",
                    response.status_code,
                    response.text,
                )
                time.sleep(1)
                continue

            data = response.json()

            content = None

            if "choices" in data:
                content = data["choices"][0]["message"]["content"]

            elif "output" in data and isinstance(data["output"], list):
                parts = []
                for block in data["output"]:
                    for item in block.get("content", []):
                        if item.get("type") == "output_text":
                            parts.append(item.get("text", ""))
                content = "".join(parts)
                
            elif isinstance(data.get("output"), str):
                content = data["output"]
            else:
                logger.error("Unrecognized LLM response schema: %s", data)
                raise ValueError("Unrecognized LLM response schema")
            
            if not content:
                logger.error("Empty content received from LLM: %s", data)
                raise ValueError("Empty content received from LLM")

            return ChatResult(
                generations=[
                    ChatGeneration(
                        message=AIMessage(content=content)
                    )
                ]
            )
            
            time.sleep(1)
        
        raise RuntimeError("LLM call failed after retries")
