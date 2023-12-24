"""
A simple wrapper for the Sakura API based on ChatGPT API
"""
import json
from typing import AsyncGenerator

from GalTransl.Backend.revChatGPT import typings as t
from GalTransl.Backend.revChatGPT.V3 import Chatbot as ChatbotV3


class Chatbot(ChatbotV3):
    """
    Sakura API
    """

    async def ask_stream_async(
        self,
        prompt: str,
        role: str = "user",
        convo_id: str = "default",
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """
        Ask a question
        """
        # Make conversation if it doesn't exist
        # if convo_id not in self.conversation:
        #     self.reset(convo_id=convo_id, system_prompt=self.system_prompt)
        # Reset Conversation for each ask to prevent Internal Server Error
        self.reset(convo_id=convo_id, system_prompt=self.system_prompt)
        self.add_to_conversation(prompt, "user", convo_id=convo_id)
        self.__truncate_conversation(convo_id=convo_id)
        # Get response
        async with self.aclient.stream(
            "post",
            self.api_address,
            headers={"Authorization": f"Bearer {kwargs.get('api_key', self.api_key)}"},
            json={
                "model": self.engine,
                "messages": self.conversation[convo_id],
                "stream": True,
                # kwargs
                "temperature": kwargs.get("temperature", self.temperature),
                "top_p": kwargs.get("top_p", self.top_p),
                "presence_penalty": kwargs.get(
                    "presence_penalty",
                    self.presence_penalty,
                ),
                "frequency_penalty": kwargs.get(
                    "frequency_penalty",
                    self.frequency_penalty,
                ),
                "n": kwargs.get("n", self.reply_count),
                "user": role,
                "max_tokens": self.get_max_tokens(convo_id=convo_id),
            },
            timeout=kwargs.get("timeout", self.timeout),
        ) as response:
            if response.status_code != 200:
                await response.aread()
                raise t.APIConnectionError(
                    f"{response.status_code} {response.reason_phrase} {response.text}",
                )

            response_role: str = ""
            full_response: str = ""
            async for line in response.aiter_lines():
                line = line.strip()
                if not line:
                    continue
                # Remove "data: "
                if line.startswith("data: "):
                    line = line[6:]
                if line == "[DONE]":
                    break
                resp: dict = json.loads(line)
                choices = resp.get("choices")
                if not choices:
                    continue
                delta = self.get_translated_text(choices=choices)
                if not delta:
                    continue
                if "role" in delta:
                    response_role = delta["role"]
                if "content" in delta:
                    content: str = delta["content"]
                    full_response += content
                    yield content
        self.add_to_conversation(full_response, response_role, convo_id=convo_id)

    def get_translated_text(self, choices: list) -> dict[str, str] | None:
        if "delta" in choices[0]:
            translated_text: dict[str, str] = choices[0].get("delta")
        if "message" in choices[0]:
            translated_text: dict[str, str] = choices[0].get("message")
        return translated_text
