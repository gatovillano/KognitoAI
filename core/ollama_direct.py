import asyncio
import json
import logging
import math
import os
import uuid
from typing import Any, AsyncIterator, Dict, Iterable, List, Optional, Sequence, Union

import httpx
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from langchain_core.rate_limiters import BaseRateLimiter
from pydantic import ConfigDict, Field


logger = logging.getLogger(__name__)


def normalize_ollama_base_url(base_url: Optional[str]) -> str:
    raw_url = (base_url or "http://host.docker.internal:11434").strip()
    if not raw_url.startswith(("http://", "https://")):
        local_hint = any(
            token in raw_url.lower()
            for token in ["localhost", "127.0.0.1", "host.docker.internal", "192.168.", "10.", "172."]
        )
        raw_url = f"{'http' if local_hint else 'https'}://{raw_url}"

    if os.path.exists("/.dockerenv") and any(token in raw_url for token in ["localhost", "127.0.0.1"]):
        raw_url = raw_url.replace("localhost", "host.docker.internal").replace("127.0.0.1", "host.docker.internal")

    return raw_url.rstrip("/")


def _coerce_stop_sequences(stop: Optional[Union[str, Sequence[str]]]) -> Optional[List[str]]:
    if stop is None:
        return None
    if isinstance(stop, str):
        return [stop]
    return [str(item) for item in stop if item is not None]


def _normalize_langchain_content(content: Any) -> Any:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return str(content or "")

    normalized: List[Dict[str, Any]] = []
    for part in content:
        if isinstance(part, str):
            normalized.append({"type": "text", "text": part})
            continue

        if not isinstance(part, dict):
            normalized.append({"type": "text", "text": str(part)})
            continue

        part_type = part.get("type")
        if part_type in {"text", "input_text"}:
            normalized.append({"type": "text", "text": part.get("text", "")})
        elif part_type in {"image_url", "input_image"}:
            image_url = part.get("image_url")
            if isinstance(image_url, dict):
                url = image_url.get("url", "")
            else:
                url = image_url or part.get("url", "")
            normalized.append({"type": "image_url", "image_url": {"url": url}})
        else:
            normalized.append(part)

    return normalized


def _langchain_tool_calls_to_openai(tool_calls: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    openai_tool_calls: List[Dict[str, Any]] = []
    for index, tool_call in enumerate(tool_calls):
        arguments = tool_call.get("args", {})
        if not isinstance(arguments, str):
            arguments = json.dumps(arguments, ensure_ascii=False)

        openai_tool_calls.append(
            {
                "id": tool_call.get("id") or f"call_{uuid.uuid4().hex}",
                "type": "function",
                "index": tool_call.get("index", index),
                "function": {
                    "name": tool_call.get("name", ""),
                    "arguments": arguments,
                },
            }
        )
    return openai_tool_calls


def convert_langchain_messages_to_openai(messages: Sequence[BaseMessage]) -> List[Dict[str, Any]]:
    converted: List[Dict[str, Any]] = []
    for message in messages:
        if isinstance(message, SystemMessage):
            converted.append({"role": "system", "content": _normalize_langchain_content(message.content)})
            continue

        if isinstance(message, HumanMessage):
            converted.append({"role": "user", "content": _normalize_langchain_content(message.content)})
            continue

        if isinstance(message, ToolMessage):
            converted.append(
                {
                    "role": "tool",
                    "content": _normalize_langchain_content(message.content),
                    "tool_call_id": message.tool_call_id,
                }
            )
            continue

        if isinstance(message, AIMessage):
            payload: Dict[str, Any] = {
                "role": "assistant",
                "content": _normalize_langchain_content(message.content),
            }
            if message.tool_calls:
                payload["tool_calls"] = _langchain_tool_calls_to_openai(message.tool_calls)
                if not payload.get("content"):
                    payload["content"] = ""
            converted.append(payload)
            continue

        role = getattr(message, "type", "user")
        converted.append({"role": role, "content": _normalize_langchain_content(message.content)})

    return converted


def _convert_messages_openai_to_ollama(messages: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    converted: List[Dict[str, Any]] = []
    for message in messages:
        ollama_message: Dict[str, Any] = {"role": message.get("role", "user")}
        content = message.get("content", "")
        tool_calls = message.get("tool_calls") or []

        if tool_calls:
            parsed_calls: List[Dict[str, Any]] = []
            for index, tool_call in enumerate(tool_calls):
                function = tool_call.get("function", {})
                raw_arguments = function.get("arguments", {})
                if isinstance(raw_arguments, str):
                    try:
                        parsed_arguments = json.loads(raw_arguments)
                    except json.JSONDecodeError:
                        parsed_arguments = {"input": raw_arguments}
                else:
                    parsed_arguments = raw_arguments or {}

                parsed_calls.append(
                    {
                        "index": tool_call.get("index", index),
                        "id": tool_call.get("id"),
                        "function": {
                            "name": function.get("name", ""),
                            "arguments": parsed_arguments,
                        },
                    }
                )

            ollama_message["content"] = ""
            ollama_message["tool_calls"] = parsed_calls
            converted.append(ollama_message)
            continue

        if isinstance(content, str):
            ollama_message["content"] = content
            if message.get("tool_call_id"):
                ollama_message["tool_call_id"] = message["tool_call_id"]
            converted.append(ollama_message)
            continue

        text_fragments: List[str] = []
        images: List[str] = []
        for item in content or []:
            if not isinstance(item, dict):
                text_fragments.append(str(item))
                continue

            part_type = item.get("type")
            if part_type == "text":
                text_fragments.append(item.get("text", ""))
            elif part_type == "image_url":
                image_url = item.get("image_url", {})
                if isinstance(image_url, dict):
                    url = image_url.get("url", "")
                else:
                    url = str(image_url)
                if url.startswith("data:"):
                    url = url.split(",", 1)[-1]
                if url:
                    images.append(url)

        ollama_message["content"] = "".join(text_fragments).strip()
        if images:
            ollama_message["images"] = images
        converted.append(ollama_message)

    return converted


def convert_openai_payload_to_ollama(payload: Dict[str, Any]) -> Dict[str, Any]:
    options = dict(payload.get("options") or {})
    converted: Dict[str, Any] = {
        "model": payload.get("model"),
        "messages": _convert_messages_openai_to_ollama(payload.get("messages") or []),
        "stream": bool(payload.get("stream", False)),
    }

    if payload.get("tools"):
        converted["tools"] = payload["tools"]

    root_option_map = {
        "format": "format",
        "keep_alive": "keep_alive",
        "think": "think",
    }
    for source_key, target_key in root_option_map.items():
        if source_key in payload:
            converted[target_key] = payload[source_key]
        elif source_key in options:
            converted[target_key] = options.pop(source_key)

    if payload.get("response_format"):
        response_format = payload["response_format"]
        format_type = response_format.get("type") if isinstance(response_format, dict) else None
        schema = response_format.get(format_type) if isinstance(response_format, dict) else None
        if isinstance(schema, dict) and schema.get("schema"):
            converted["format"] = schema["schema"]

    option_aliases = {
        "temperature": "temperature",
        "top_p": "top_p",
        "top_k": "top_k",
        "min_p": "min_p",
        "presence_penalty": "presence_penalty",
        "frequency_penalty": "frequency_penalty",
        "seed": "seed",
        "repeat_penalty": "repeat_penalty",
        "repeat_last_n": "repeat_last_n",
        "num_ctx": "num_ctx",
        "num_thread": "num_thread",
        "num_gpu": "num_gpu",
        "num_predict": "num_predict",
        "stop": "stop",
    }

    for source_key, target_key in option_aliases.items():
        if source_key in payload and payload[source_key] is not None:
            options[target_key] = payload[source_key]

    # Mapear max_tokens a num_predict (Ollama no acepta max_tokens)
    # Verificar tanto en payload root como en options dict
    max_tokens_value = None
    if "max_tokens" in payload and payload["max_tokens"] is not None:
        max_tokens_value = payload["max_tokens"]
    elif "max_tokens" in options and options["max_tokens"] is not None:
        max_tokens_value = options.pop("max_tokens")  # Eliminar de options
    if max_tokens_value is not None:
        options["num_predict"] = max_tokens_value

    if options:
        converted["options"] = options

    return converted


def _convert_ollama_tool_calls_to_langchain(tool_calls: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    converted: List[Dict[str, Any]] = []
    for tool_call in tool_calls:
        function = tool_call.get("function") or {}
        arguments = function.get("arguments") or {}
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                arguments = {"input": arguments}

        converted.append(
            {
                "name": function.get("name", ""),
                "args": arguments,
                "id": tool_call.get("id") or f"call_{uuid.uuid4().hex}",
                "type": "tool_call",
            }
        )
    return converted


def _build_response_metadata(data: Dict[str, Any]) -> Dict[str, Any]:
    usage = {
        "input_tokens": int(data.get("prompt_eval_count", 0) or 0),
        "output_tokens": int(data.get("eval_count", 0) or 0),
    }
    usage["total_tokens"] = usage["input_tokens"] + usage["output_tokens"]

    metadata = {
        "model": data.get("model"),
        "done": data.get("done", False),
        "usage": usage,
    }

    thinking = (data.get("message") or {}).get("thinking")
    if thinking:
        metadata["thinking"] = thinking

    return metadata


def build_ai_message_from_ollama(data: Dict[str, Any]) -> AIMessage:
    message = data.get("message") or {}
    tool_calls = _convert_ollama_tool_calls_to_langchain(message.get("tool_calls") or [])
    additional_kwargs: Dict[str, Any] = {}
    if message.get("thinking"):
        additional_kwargs["thinking"] = message["thinking"]

    return AIMessage(
        content=message.get("content", ""),
        tool_calls=tool_calls,
        additional_kwargs=additional_kwargs,
        response_metadata=_build_response_metadata(data),
    )


async def _async_retry_backoff(attempt: int) -> None:
    await asyncio.sleep(min(2.0, 0.5 * (2 ** max(0, attempt - 1))))


def _should_retry(exc: Exception, response: Optional[httpx.Response] = None) -> bool:
    if response is not None:
        return response.status_code in {408, 409, 425, 429, 500, 502, 503, 504}
    return isinstance(exc, (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout, httpx.RemoteProtocolError))


def _is_cloudflare_524(exc: Exception) -> bool:
    if isinstance(exc, httpx.HTTPStatusError) and exc.response is not None:
        return exc.response.status_code == 524
    message = str(exc).lower()
    return "(524)" in message or "error code 524" in message or ("cloudflare" in message and "timeout" in message)


async def ollama_embeddings(
    *,
    base_url: str,
    model: str,
    input_data: Union[str, List[str]],
    timeout: float,
    max_retries: int,
) -> List[List[float]]:
    normalized_url = normalize_ollama_base_url(base_url)
    inputs = input_data if isinstance(input_data, list) else [input_data]
    endpoint_candidates = ["/api/embed", "/api/embeddings"] if len(inputs) > 1 else ["/api/embeddings", "/api/embed"]

    last_error: Optional[Exception] = None
    async with httpx.AsyncClient(timeout=timeout) as client:
        for endpoint in endpoint_candidates:
            payload = {"model": model}
            if endpoint.endswith("/embed"):
                payload["input"] = inputs
            else:
                payload["prompt"] = inputs[0]

            for attempt in range(max_retries + 1):
                try:
                    response = await client.post(f"{normalized_url}{endpoint}", json=payload)
                    if response.status_code == 404 and endpoint == "/api/embeddings":
                        break
                    response.raise_for_status()
                    data = response.json()
                    if isinstance(data.get("embedding"), list):
                        return [data["embedding"]]
                    if isinstance(data.get("embeddings"), list):
                        if data["embeddings"] and isinstance(data["embeddings"][0], dict):
                            return [item.get("embedding", []) for item in data["embeddings"]]
                        return data["embeddings"]
                    raise ValueError("Ollama devolvio un formato de embeddings no reconocido")
                except Exception as exc:
                    last_error = exc
                    response = exc.response if isinstance(exc, httpx.HTTPStatusError) else None
                    if attempt >= max_retries or not _should_retry(exc, response):
                        if response is not None and response.status_code == 404 and endpoint == "/api/embeddings":
                            break
                        raise
                    await _async_retry_backoff(attempt + 1)

    if last_error:
        raise last_error
    raise RuntimeError("No fue posible obtener embeddings desde Ollama")


class OllamaDirectChatModel(BaseChatModel):
    model_name: str
    base_url: str
    fallback_base_url: Optional[str] = None
    temperature: float = 0.0
    streaming: bool = True
    timeout: float = 300.0
    max_tokens: Optional[int] = None
    max_retries: int = 0
    top_p: Optional[float] = None
    keep_alive: Optional[Union[int, str]] = None
    extra_body: Dict[str, Any] = Field(default_factory=dict)
    rate_limiter: Optional[BaseRateLimiter] = None
    # API key para Ollama Cloud (https://docs.ollama.com/cloud)
    # Se envía como: Authorization: Bearer <api_key>
    api_key: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    def _build_auth_headers(self) -> Dict[str, str]:
        """Construye el header de autenticación Bearer para Ollama Cloud."""
        if self.api_key:
            return {"Authorization": f"Bearer {self.api_key}"}
        return {}

    @property
    def _llm_type(self) -> str:
        return "ollama-direct"

    @property
    def _identifying_params(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "base_url": self.base_url,
            "fallback_base_url": self.fallback_base_url,
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
                logger.warning("No se pudo convertir una herramienta a formato OpenAI para Ollama", exc_info=True)

        binding_kwargs = {"tools": formatted_tools, **kwargs}
        if tool_choice is not None:
            binding_kwargs["tool_choice"] = tool_choice
        return self.bind(**binding_kwargs)

    def get_num_tokens_from_messages(self, messages: List[BaseMessage], tools: Optional[Sequence[Any]] = None) -> int:
        serialized = json.dumps(convert_langchain_messages_to_openai(messages), ensure_ascii=False)
        tool_payload = json.dumps(list(tools or []), ensure_ascii=False) if tools else ""
        approx = math.ceil((len(serialized) + len(tool_payload)) / 4)
        return max(1, approx)

    def _prepare_payload(
        self,
        messages: Sequence[BaseMessage],
        *,
        stop: Optional[Union[str, Sequence[str]]] = None,
        stream: bool,
        tools: Optional[Sequence[Dict[str, Any]]] = None,
        response_format: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        options: Dict[str, Any] = {}
        if self.temperature is not None:
            options["temperature"] = self.temperature
        if self.top_p is not None:
            options["top_p"] = self.top_p
        if self.max_tokens is not None:
            options["max_tokens"] = self.max_tokens

        stop_sequences = _coerce_stop_sequences(stop)
        if stop_sequences:
            options["stop"] = stop_sequences

        if isinstance(self.extra_body, dict):
            options.update({k: v for k, v in self.extra_body.items() if k not in {"model"}})

        for key in [
            "temperature",
            "top_p",
            "top_k",
            "min_p",
            "seed",
            "repeat_penalty",
            "repeat_last_n",
            "num_ctx",
            "num_thread",
            "num_gpu",
            "presence_penalty",
            "frequency_penalty",
            "stop",
            "max_tokens",
            "num_predict",
            "keep_alive",
            "think",
            "format",
        ]:
            value = kwargs.get(key)
            if value is not None:
                options[key] = value

        if options.get("include_reasoning") is not None and "think" not in options:
            options["think"] = bool(options.pop("include_reasoning"))
        if options.get("reasoning") is not None and "think" not in options:
            options["think"] = bool(options.pop("reasoning"))
        if options.get("thinking") is not None and "think" not in options:
            thinking_value = options.pop("thinking")
            options["think"] = bool(thinking_value) if not isinstance(thinking_value, dict) else True

        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": convert_langchain_messages_to_openai(messages),
            "stream": stream,
            "options": options,
        }
        if tools:
            payload["tools"] = list(tools)
        if response_format:
            payload["response_format"] = response_format
        if self.keep_alive is not None and "keep_alive" not in payload:
            payload["keep_alive"] = self.keep_alive

        return convert_openai_payload_to_ollama(payload)

    async def _acquire_rate_limit(self) -> None:
        if self.rate_limiter is not None:
            await self.rate_limiter.aacquire()

    def _acquire_rate_limit_sync(self) -> None:
        if self.rate_limiter is not None:
            self.rate_limiter.acquire()

    async def _agenerate(self, messages: List[BaseMessage], stop: Optional[List[str]] = None, run_manager=None, **kwargs: Any) -> ChatResult:
        await self._acquire_rate_limit()
        _tools = kwargs.pop("tools", None)
        _response_format = kwargs.pop("response_format", None)
        payload = self._prepare_payload(
            messages,
            stop=stop,
            stream=False,
            tools=_tools,
            response_format=_response_format,
            **kwargs,
        )

        last_error: Optional[Exception] = None
        auth_headers = self._build_auth_headers()
        async with httpx.AsyncClient(timeout=self.timeout, headers=auth_headers) as client:
            for attempt in range(self.max_retries + 1):
                try:
                    response = await client.post(f"{self.base_url}/api/chat", json=payload)
                    response.raise_for_status()
                    ai_message = build_ai_message_from_ollama(response.json())
                    return ChatResult(generations=[ChatGeneration(message=ai_message)])
                except Exception as exc:
                    last_error = exc
                    response = exc.response if isinstance(exc, httpx.HTTPStatusError) else None
                    if attempt >= self.max_retries or not _should_retry(exc, response):
                        raise
                    await _async_retry_backoff(attempt + 1)

        if last_error:
            raise last_error
        raise RuntimeError("Fallo inesperado al llamar a Ollama")

    def _generate(self, messages: List[BaseMessage], stop: Optional[List[str]] = None, run_manager=None, **kwargs: Any) -> ChatResult:
        self._acquire_rate_limit_sync()
        _tools = kwargs.pop("tools", None)
        _response_format = kwargs.pop("response_format", None)
        payload = self._prepare_payload(
            messages,
            stop=stop,
            stream=False,
            tools=_tools,
            response_format=_response_format,
            **kwargs,
        )

        last_error: Optional[Exception] = None
        auth_headers = self._build_auth_headers()
        with httpx.Client(timeout=self.timeout, headers=auth_headers) as client:
            for attempt in range(self.max_retries + 1):
                try:
                    response = client.post(f"{self.base_url}/api/chat", json=payload)
                    response.raise_for_status()
                    ai_message = build_ai_message_from_ollama(response.json())
                    return ChatResult(generations=[ChatGeneration(message=ai_message)])
                except Exception as exc:
                    last_error = exc
                    response = exc.response if isinstance(exc, httpx.HTTPStatusError) else None
                    if attempt >= self.max_retries or not _should_retry(exc, response):
                        raise
                    asyncio.run(_async_retry_backoff(attempt + 1))

        if last_error:
            raise last_error
        raise RuntimeError("Fallo inesperado al llamar a Ollama")

    async def _astream(self, messages: List[BaseMessage], stop: Optional[List[str]] = None, run_manager=None, **kwargs: Any) -> AsyncIterator[ChatGenerationChunk]:
        await self._acquire_rate_limit()
        _tools = kwargs.pop("tools", None)
        _response_format = kwargs.pop("response_format", None)
        payload = self._prepare_payload(
            messages,
            stop=stop,
            stream=True,
            tools=_tools,
            response_format=_response_format,
            **kwargs,
        )

        base_candidates: List[str] = [self.base_url]
        if self.fallback_base_url and self.fallback_base_url != self.base_url:
            base_candidates.append(self.fallback_base_url)

        last_error: Optional[Exception] = None
        auth_headers = self._build_auth_headers()
        async with httpx.AsyncClient(timeout=self.timeout, headers=auth_headers) as client:
            for base_index, base_url in enumerate(base_candidates):
                for attempt in range(self.max_retries + 1):
                    yielded_any_chunk = False
                    try:
                        async with client.stream("POST", f"{base_url}/api/chat", json=payload) as response:
                            if response.status_code >= 400:
                                error_bytes = await response.aread()
                                error_text = error_bytes.decode("utf-8", errors="replace") if error_bytes else ""
                                raise RuntimeError(
                                    f"Ollama /api/chat stream error ({response.status_code}): {error_text[:2000]}"
                                )

                            async for line in response.aiter_lines():
                                if not line:
                                    continue
                                yielded_any_chunk = True
                                data = json.loads(line)
                                message = data.get("message") or {}
                                additional_kwargs: Dict[str, Any] = {}
                                if message.get("thinking"):
                                    additional_kwargs["thinking"] = message["thinking"]

                                tool_calls = _convert_ollama_tool_calls_to_langchain(message.get("tool_calls") or [])
                                chunk_message = AIMessageChunk(
                                    content=message.get("content", ""),
                                    additional_kwargs=additional_kwargs,
                                    tool_calls=tool_calls,
                                    response_metadata=_build_response_metadata(data),
                                )
                                yield ChatGenerationChunk(message=chunk_message)
                            return
                    except Exception as exc:
                        last_error = exc

                        # Si ya hubo chunks, no podemos reintentar/fallback de forma segura
                        if yielded_any_chunk:
                            raise

                        # Fallback dedicado para 524 de Cloudflare (sin gastar retries del origen primario)
                        if (
                            base_index == 0
                            and len(base_candidates) > 1
                            and _is_cloudflare_524(exc)
                        ):
                            logger.warning(
                                "⚠️ Cloudflare 524 detectado en Ollama stream. Reintentando con URL directa: %s",
                                base_candidates[1],
                            )
                            break

                        response = exc.response if isinstance(exc, httpx.HTTPStatusError) else None
                        if attempt >= self.max_retries or not _should_retry(exc, response):
                            # Si hay una URL de fallback y aún no la probamos, pasar a ella
                            if base_index == 0 and len(base_candidates) > 1:
                                logger.warning(
                                    "⚠️ Reintentando stream de Ollama con URL fallback tras error: %s",
                                    exc,
                                )
                                break
                            raise

                        await _async_retry_backoff(attempt + 1)

        if last_error:
            raise last_error
        raise RuntimeError("Fallo inesperado al hacer stream con Ollama")
