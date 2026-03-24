from __future__ import annotations

import asyncio
from typing import Any, List

from injector import inject, singleton
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage

from argus.settings.settings import Settings


def _build_messages(messages: List[dict]) -> List[BaseMessage]:
    """Convert list of {role, content} dicts to LangChain message objects."""
    lc_map = {"system": SystemMessage, "user": HumanMessage, "assistant": AIMessage}
    return [lc_map.get(m["role"], HumanMessage)(content=m["content"]) for m in messages]


@singleton
class LLMComponent:
    """
    Swappable LLM provider singleton.

    Supported modes (set via settings.llm.mode):
      openai   — ChatOpenAI (GPT-4o, default)
      gemini   — ChatGoogleGenerativeAI
      bedrock  — ChatBedrock (AWS)
      ollama   — ChatOllama (local)

    Public interface:
      await llm.achat(messages)    → str   (chat completion)
      await llm.acomplete(prompt)  → str   (single-turn completion)
    """

    @inject
    def __init__(self, settings: Settings) -> None:
        self._cfg = settings.llm
        self._client = self._build_client()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _build_client(self) -> Any:
        mode = self._cfg.mode
        if mode == "openai":
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=self._cfg.model,
                temperature=self._cfg.temperature,
                max_tokens=self._cfg.max_tokens,
                streaming=True,
            )
        if mode == "gemini":
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
            except ImportError:
                raise ImportError("Install langchain-google-genai for Gemini support.")
            return ChatGoogleGenerativeAI(
                model=self._cfg.model,
                temperature=self._cfg.temperature,
                max_output_tokens=self._cfg.max_tokens,
            )
        if mode == "bedrock":
            try:
                from langchain_aws import ChatBedrock
            except ImportError:
                raise ImportError("Install langchain-aws for Bedrock support.")
            return ChatBedrock(model_id=self._cfg.model)
        if mode == "ollama":
            try:
                from langchain_ollama import ChatOllama
            except ImportError:
                raise ImportError("Install langchain-ollama for Ollama support.")
            return ChatOllama(
                model=self._cfg.model,
                temperature=self._cfg.temperature,
            )
        raise ValueError(f"Unknown LLM mode: {mode!r}. Choose openai | gemini | bedrock | ollama")

    # ── Public API ────────────────────────────────────────────────────────────

    async def achat(self, messages: List[dict]) -> str:
        """
        Multi-turn chat completion.

        Args:
            messages: list of {"role": "system"|"user"|"assistant", "content": str}

        Returns:
            Assistant response text.
        """
        lc_messages = _build_messages(messages)
        response = await self._client.ainvoke(lc_messages)
        return response.content

    async def acomplete(self, prompt: str) -> str:
        """
        Single-turn text completion (wraps achat with a single user message).

        Args:
            prompt: the full prompt string.

        Returns:
            Completion text.
        """
        return await self.achat([{"role": "user", "content": prompt}])

    @property
    def model_name(self) -> str:
        return self._cfg.model

    @property
    def mode(self) -> str:
        return self._cfg.mode
