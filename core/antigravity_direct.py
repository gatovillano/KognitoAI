# core/antigravity_direct.py

import asyncio
import json
import logging
import threading
import uuid
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional, Sequence, Union

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.messages.tool import ToolCallChunk
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from langchain_core.rate_limiters import BaseRateLimiter
from pydantic import Field

from core.antigravity_client import AntigravityClient
from core.ollama_direct import convert_langchain_messages_to_openai

logger = logging.getLogger(__name__)


class AntigravityChatModel(BaseChatModel):
    """
    Modelo de chat nativo de LangChain para Google Antigravity.
    Se comunica directamente con AntigravityClient sin depender de intermediarios.
    Soporta generación estructurada, streaming SSE, tool calling y razonamiento nativo (thinking).
    """
    model_name: str = Field(default="antigravity/gemini-3-flash")
    temperature: Optional[float] = Field(default=None)
    timeout: float = Field(default=120.0)
    max_retries: int = Field(default=2)
    rate_limiter: Optional[BaseRateLimiter] = Field(default=None)
    extra_body: Optional[Dict[str, Any]] = Field(default=None)
    custom_llm_provider: str = Field(default="antigravity")

    @property
    def _llm_type(self) -> str:
        return "antigravity"

    @property
    def _identifying_params(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "temperature": self.temperature,
            "custom_llm_provider": self.custom_llm_provider,
        }

    def bind_tools(self, tools: Sequence[Any], *, tool_choice: Optional[Any] = None, **kwargs: Any):
        formatted_tools: List[Dict[str, Any]] = []
        for tool in tools:
            if isinstance(tool, dict):
                formatted_tools.append(tool)
                continue
            try:
                from langchain_core.utils.function_calling import convert_to_openai_tool
                formatted_tools.append(convert_to_openai_tool(tool))
            except Exception:
                logger.warning("No se pudo convertir una herramienta a formato OpenAI para Antigravity", exc_info=True)

        binding_kwargs = {"tools": formatted_tools, **kwargs}
        if tool_choice is not None:
            binding_kwargs["tool_choice"] = tool_choice
        return self.bind(**binding_kwargs)

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager=None,
        **kwargs: Any,
    ) -> ChatResult:
        tools = kwargs.pop("tools", None)
        openai_messages = convert_langchain_messages_to_openai(messages)

        response = AntigravityClient.completion(
            model=self.model_name,
            messages=openai_messages,
            tools=tools,
            stream=False,
            temperature=self.temperature,
            **kwargs,
        )

        choice = response.choices[0]
        content = choice.message.content or ""
        additional_kwargs: Dict[str, Any] = {}
        if hasattr(choice.message, "reasoning_content") and choice.message.reasoning_content:
            additional_kwargs["thinking"] = choice.message.reasoning_content
            additional_kwargs["reasoning_content"] = choice.message.reasoning_content

        tool_calls: List[Dict[str, Any]] = []
        if hasattr(choice.message, "tool_calls") and choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                fn_name = tc.function.name if hasattr(tc, "function") else tc.get("function", {}).get("name")
                fn_args = tc.function.arguments if hasattr(tc, "function") else tc.get("function", {}).get("arguments")
                if isinstance(fn_args, str):
                    try:
                        args_dict = json.loads(fn_args)
                    except Exception:
                        args_dict = {"input": fn_args}
                else:
                    args_dict = fn_args or {}

                tc_id = getattr(tc, "id", None) or (tc.get("id") if isinstance(tc, dict) else None) or f"call_{uuid.uuid4().hex[:8]}"
                tool_call_dict = {
                    "name": fn_name,
                    "args": args_dict,
                    "id": tc_id,
                    "type": "tool_call",
                }
                tool_calls.append(tool_call_dict)

        ai_message = AIMessage(
            content=content,
            additional_kwargs=additional_kwargs,
            tool_calls=tool_calls,
        )
        return ChatResult(generations=[ChatGeneration(message=ai_message)])

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager=None,
        **kwargs: Any,
    ) -> ChatResult:
        if self.rate_limiter is not None:
            await self.rate_limiter.aacquire()
        return await asyncio.to_thread(self._generate, messages, stop=stop, run_manager=run_manager, **kwargs)

    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager=None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        tools = kwargs.pop("tools", None)
        openai_messages = convert_langchain_messages_to_openai(messages)
        gen = AntigravityClient.completion(
            model=self.model_name,
            messages=openai_messages,
            tools=tools,
            stream=True,
            temperature=self.temperature,
            **kwargs,
        )
        for chunk in gen:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            content = delta.content or ""
            additional_kwargs: Dict[str, Any] = {}
            if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                additional_kwargs["thinking"] = delta.reasoning_content
                additional_kwargs["reasoning_content"] = delta.reasoning_content

            tool_call_chunks = []
            if hasattr(delta, "tool_calls") and delta.tool_calls:
                for tc in delta.tool_calls:
                    name = tc.function.name if hasattr(tc, "function") else tc.get("function", {}).get("name")
                    args = tc.function.arguments if hasattr(tc, "function") else tc.get("function", {}).get("arguments")
                    tc_id = getattr(tc, "id", None) or (tc.get("id") if isinstance(tc, dict) else None)
                    idx = getattr(tc, "index", 0) if hasattr(tc, "index") else (tc.get("index", 0) if isinstance(tc, dict) else 0)
                    tool_call_chunks.append(
                        ToolCallChunk(
                            name=name,
                            args=args or "",
                            id=tc_id,
                            index=idx,
                        )
                    )

            chunk_message = AIMessageChunk(
                content=content,
                additional_kwargs=additional_kwargs,
                tool_call_chunks=tool_call_chunks,
            )
            yield ChatGenerationChunk(message=chunk_message)

    async def _astream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager=None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatGenerationChunk]:
        if self.rate_limiter is not None:
            await self.rate_limiter.aacquire()

        tools = kwargs.pop("tools", None)
        openai_messages = convert_langchain_messages_to_openai(messages)

        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()

        def _worker():
            try:
                gen = AntigravityClient.completion(
                    model=self.model_name,
                    messages=openai_messages,
                    tools=tools,
                    stream=True,
                    temperature=self.temperature,
                    **kwargs,
                )
                for chunk in gen:
                    loop.call_soon_threadsafe(queue.put_nowait, ("item", chunk))
                loop.call_soon_threadsafe(queue.put_nowait, ("done", None))
            except Exception as exc:
                loop.call_soon_threadsafe(queue.put_nowait, ("error", exc))

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

        while True:
            event_type, payload = await queue.get()
            if event_type == "done":
                break
            elif event_type == "error":
                raise payload
            elif event_type == "item":
                chunk = payload
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                content = delta.content or ""
                additional_kwargs = {}
                if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                    additional_kwargs["thinking"] = delta.reasoning_content
                    additional_kwargs["reasoning_content"] = delta.reasoning_content

                tool_call_chunks = []
                if hasattr(delta, "tool_calls") and delta.tool_calls:
                    for tc in delta.tool_calls:
                        name = tc.function.name if hasattr(tc, "function") else tc.get("function", {}).get("name")
                        args = tc.function.arguments if hasattr(tc, "function") else tc.get("function", {}).get("arguments")
                        tc_id = getattr(tc, "id", None) or (tc.get("id") if isinstance(tc, dict) else None)
                        idx = getattr(tc, "index", 0) if hasattr(tc, "index") else (tc.get("index", 0) if isinstance(tc, dict) else 0)
                        tool_call_chunks.append(
                            ToolCallChunk(
                                name=name,
                                args=args or "",
                                id=tc_id,
                                index=idx,
                            )
                        )

                chunk_message = AIMessageChunk(
                    content=content,
                    additional_kwargs=additional_kwargs,
                    tool_call_chunks=tool_call_chunks,
                )
                yield ChatGenerationChunk(message=chunk_message)
