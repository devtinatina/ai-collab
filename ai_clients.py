"""AI Client modules for OpenAI and Anthropic"""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass

from openai import OpenAI
from anthropic import Anthropic


@dataclass
class Message:
    role: str
    content: str


class AIClient(ABC):
    """Base class for AI clients"""

    @abstractmethod
    def chat(self, messages: list[Message], system_prompt: str = "") -> str:
        pass


class OpenAIClient(AIClient):
    """OpenAI API Client (Manager/PM role)"""

    def __init__(self, api_key: str = None, model: str = "gpt-4o", temperature: float = 0.3):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        self.client = OpenAI(api_key=self.api_key)
        self.model = model
        self.temperature = temperature

    def chat(self, messages: list[Message], system_prompt: str = "") -> str:
        formatted_messages = []

        if system_prompt:
            formatted_messages.append({"role": "system", "content": system_prompt})

        for msg in messages:
            formatted_messages.append({"role": msg.role, "content": msg.content})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=formatted_messages,
            temperature=self.temperature,
        )

        return response.choices[0].message.content


class AnthropicClient(AIClient):
    """Anthropic Claude API Client (Developer role)"""

    def __init__(self, api_key: str = None, model: str = "claude-sonnet-4-20250514", temperature: float = 0.7):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key is required")
        self.client = Anthropic(api_key=self.api_key)
        self.model = model
        self.temperature = temperature

    def chat(self, messages: list[Message], system_prompt: str = "") -> str:
        formatted_messages = []

        for msg in messages:
            formatted_messages.append({"role": msg.role, "content": msg.content})

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system_prompt if system_prompt else "",
            messages=formatted_messages,
            temperature=self.temperature,
        )

        return response.content[0].text


def create_client(provider: str, **kwargs) -> AIClient:
    """Factory function to create AI clients"""
    if provider == "openai":
        return OpenAIClient(**kwargs)
    elif provider == "anthropic":
        return AnthropicClient(**kwargs)
    else:
        raise ValueError(f"Unknown provider: {provider}")
