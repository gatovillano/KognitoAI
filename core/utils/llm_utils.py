import logging
import json
import re
from typing import Any, Optional, Union, List, TypeVar, Type, Sequence, cast
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    MessageLikeRepresentation,
    ToolMessage,
    HumanMessage,
)
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable

# Usar el logger de la aplicación para mayor visibilidad
logger = logging.getLogger("core.utils.llm_utils")
# Forzar nivel WARNING para producción
logger.setLevel(logging.WARNING)

# --- Helper functions for OpenRouter compatibility ---


def is_openrouter_model(llm):
    """Check if the given LLM is an OpenRouter model."""
    # Check model_name attribute
    model_name = getattr(llm, "model_name", "") or ""
    if isinstance(model_name, str) and "openrouter" in model_name.lower():
        return True
    # Check base_url or api_base
    base_url = getattr(llm, "base_url", "") or getattr(llm, "api_base", "") or ""
    if isinstance(base_url, str) and "openrouter" in base_url.lower():
        return True
    # Check if it is a ChatLiteLLM and model string contains openrouter
    if hasattr(llm, "model") and "openrouter" in str(llm.model).lower():
        return True
    return False


def safe_bind_tools(llm, tools, **kwargs):
    """Bind tools to LLM, handling OpenRouter lack of tool_choice support."""
    if is_openrouter_model(llm):
        # OpenRouter does not support tool_choice parameter. Remove it if present.
        kwargs.pop("tool_choice", None)
        # Also, we might need to avoid other parameters that cause issues.
        # Just bind tools without extra args.
        try:
            return llm.bind_tools(tools)
        except Exception as e:
            logger.warning(
                f"⚠️ [LLM Utils] Error binding tools for OpenRouter: {e}. Trying without any args."
            )
            # Fallback: try to bind tools with minimal arguments
            return llm.bind_tools(tools)
    else:
        return llm.bind_tools(tools, **kwargs)


def safe_json_loads(content: str) -> Any:
    """
    Intenta cargar JSON de forma robusta, manejando bloques markdown y texto extra.
    """
    if not content:
        return None

    content = content.strip()

    if not content:
        return None

    # 1. Intentar extraer de bloques markdown
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()

    # 2. Buscar el inicio del JSON
    start_idx = content.find("{")
    start_arr = content.find("[")

    if start_idx == -1 and start_arr == -1:
        return json.loads(content)  # Dejar que falle normalmente si no hay inicio claro

    if start_idx == -1:
        start_idx = start_arr
    elif start_arr != -1:
        start_idx = min(start_idx, start_arr)

    content_from_start = content[start_idx:]

    try:
        # raw_decode permite ignorar texto extra después del JSON válido
        decoder = json.JSONDecoder()
        obj, _ = decoder.raw_decode(content_from_start)
        return obj
    except json.JSONDecodeError:
        pass

    # 3. Fallback: Limpieza con regex para encontrar el bloque exterior
    # Intentar encontrar el bloque más grande que parezca JSON
    json_match = re.search(r"(\{.*\}|\[.*\])", content, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except:
            pass

    # Último intento con el contenido original o procesado por markdown
    return json.loads(content)


async def invoke_structured_output(
    llm: BaseChatModel, schema: Any, prompt: str, retry_config: dict = None
) -> Any:
    """Invokes an LLM with structured output, falling back to manual JSON parsing if needed."""
    try:
        # 1. Intentar con el método estándar (herramientas)
        # Deshabilitamos streaming para asegurar captura completa en logs y estabilidad JSON

        # FIX: OpenRouter compatibility for tool_choice
        # Muchos modelos en OpenRouter fallan con métodos de herramientas automáticos.
        is_openrouter = is_openrouter_model(llm)

        try:
            if is_openrouter:
                # Omitimos explícitamente cualquier tool_choice y usamos json_mode para OpenRouter
                # para maximizar la compatibilidad con modelos especializados.
                model = llm.with_structured_output(schema, method="json_mode")
            else:
                model = llm.with_structured_output(schema)
        except Exception as e:
            # Fallback a json_mode si el método estándar falla
            logger.warning(
                f"⚠️ [Structured Output] Failed to create model with method='tool_calling': {e}. Retrying with 'json_mode'."
            )
            model = llm.with_structured_output(schema, method="json_mode")

        if hasattr(model, "streaming"):
            model.streaming = False

        if retry_config:
            model = model.with_retry(**retry_config)

        # Intentar invocar con un HumanMessage explícito
        result = await model.ainvoke([HumanMessage(content=prompt)])

        if result is None:
            logger.warning(
                "⚠️ [Structured Output] Standard method returned None. Forcing manual fallback."
            )
            raise ValueError("LLM returned None in structured output mode")

        logger.debug(f"✅ [Structured Output] Standard method succeeded.")
        return result
    except Exception as e:
        error_str = str(e)
        # Si es un error de límite de tokens, no es culpa del método estructurado, lo dejamos pasar
        if is_token_limit_exceeded(e):
            raise e
        logger.warning(
            f"⚠️ [Structured Output] Standard method failed: {e}. Body: {error_str[:500]}. Attempting manual fallback."
        )

        # Manual parsing logic
        schema_definition = schema.schema() if hasattr(schema, "schema") else {}
        schema_json = json.dumps(schema_definition, indent=2)

        # Crear un ejemplo dinámico para guiar al LLM
        example = {}
        if schema_definition and "properties" in schema_definition:
            for prop, details in schema_definition["properties"].items():
                prop_type = details.get("type")
                description = details.get("description", f"un valor para {prop}")
                if prop_type == "string":
                    example[prop] = (
                        f"Un valor de tipo string que representa {description}"
                    )
                elif prop_type == "boolean":
                    example[prop] = False
                elif prop_type == "integer" or prop_type == "number":
                    example[prop] = 0
                elif prop_type == "array":
                    example[prop] = []
                else:
                    example[prop] = "..."

        example_json = json.dumps(example, indent=2, ensure_ascii=False)

        manual_prompt = (
            f"{prompt}\n\n"
            f"IMPORTANTE: Tu respuesta DEBE ser únicamente un objeto JSON válido que se ajuste al siguiente esquema. No incluyas ninguna otra explicación, texto introductorio, bloques de razonamiento o markdown fuera del JSON.\n\n"
            f"Esquema JSON requerido:\n{schema_json}\n\n"
            f"Ejemplo de un objeto JSON con el formato correcto:\n{example_json}\n\n"
            f"Ahora, basándote en la conversación, genera el objeto JSON final:"
        )

        # Crear una versión del LLM sin streaming y sin razonamiento para el fallback manual
        llm_no_stream = llm.copy() if hasattr(llm, "copy") else llm
        if hasattr(llm_no_stream, "streaming"):
            llm_no_stream.streaming = False

        # Forzar extra_body para desactivar razonamiento si es un ChatLiteLLM
        if hasattr(llm_no_stream, "extra_body"):
            if not llm_no_stream.extra_body:
                llm_no_stream.extra_body = {}
            llm_no_stream.extra_body["include_reasoning"] = False

        response = await llm_no_stream.ainvoke([HumanMessage(content=manual_prompt)])

        content = response.content if hasattr(response, "content") else str(response)
        logger.debug(
            f"🔍 [Structured Output] Manual fallback raw content: {content[:500]}..."
        )

        # Limpieza previa: eliminar bloques de código markdown si existen
        clean_content = content.strip()
        if clean_content.startswith("```json"):
            clean_content = clean_content[7:]
        elif clean_content.startswith("```"):
            clean_content = clean_content[3:]

        if clean_content.endswith("```"):
            clean_content = clean_content[:-3]

        clean_content = clean_content.strip()

        # Intentar extraer JSON de la respuesta (ahora más flexible)
        try:
            data = safe_json_loads(clean_content)
            if data is None:
                raise ValueError("Failed to parse JSON from LLM response")
            # Usar parse_obj si está disponible (Pydantic V2), si no, usar el constructor
            if hasattr(schema, "parse_obj"):
                return schema.parse_obj(data)
            # Pydantic V1/V2 __init__
            return schema(**data)
        except Exception as e3:
            logger.error(
                f"❌ [Structured Output] Manual parsing/validation failed: {e3}. Content: {clean_content[:500]}..."
            )
            raise e3


def is_token_limit_exceeded(exception: Exception, model_name: str = None) -> bool:
    """Determine if an exception indicates a token/context limit was exceeded."""
    err_str = str(exception).lower()
    return "maximum context length" in err_str or "context_length_exceeded" in err_str


def remove_up_to_last_ai_message(
    messages: List[MessageLikeRepresentation],
) -> List[MessageLikeRepresentation]:
    """Truncate message history by removing up to the last AI message (and its tool outputs if any)."""
    for i in range(len(messages) - 1, -1, -1):
        msg = messages[i]
        if isinstance(msg, AIMessage):
            # Found the last AI message.
            # If it has tool calls, we must also skip the subsequent ToolMessages to avoid orphan tool outputs.
            start_index = i + 1
            if msg.tool_calls:
                while start_index < len(messages) and isinstance(
                    messages[start_index], ToolMessage
                ):
                    start_index += 1

            return messages[start_index:]
    return messages


async def prune_messages_to_fit_token_limit(
    messages: List[BaseMessage],
    llm: BaseChatModel,
    max_tokens: int,
    min_messages_to_keep: int = 1,
    keep_ratio: float = 0.5,
) -> List[BaseMessage]:
    """
    Prunes the list of messages to fit within the specified token limit.
    It summarizes older messages to preserve context while keeping recent messages intact.
    """
    if not messages:
        return []

    try:
        current_tokens = llm.get_num_tokens_from_messages(messages)
    except Exception as e:
        logger.warning(f"Error counting tokens: {e}. Assuming limit exceeded.")
        current_tokens = max_tokens + 1

    if current_tokens <= max_tokens:
        return messages

    logger.warning(
        f"⚠️ [LLM Utils] Message history ({current_tokens} tokens) exceeds max_tokens ({max_tokens} tokens). Pruning and summarizing..."
    )

    system_messages = [msg for msg in messages if msg.type == "system"]
    other_messages = [msg for msg in messages if msg.type != "system"]

    # Group messages into atomic blocks to preserve tool call sequences
    blocks: List[List[BaseMessage]] = []
    i = 0
    while i < len(other_messages):
        msg = other_messages[i]
        block = [msg]
        i += 1

        # If this is an AIMessage with tool calls, include subsequent ToolMessages in the same block
        if isinstance(msg, AIMessage) and msg.tool_calls:
            while i < len(other_messages) and isinstance(
                other_messages[i], ToolMessage
            ):
                block.append(other_messages[i])
                i += 1

        blocks.append(block)

    # Determine which blocks to keep (most recent ones)
    messages_to_keep: List[BaseMessage] = []

    # Iterate backwards through blocks
    for i in range(len(blocks) - 1, -1, -1):
        block_to_add = blocks[i]

        # Calculate tokens for the proposed state (system + new block + kept messages)
        # Note: We add block_to_add at the beginning of messages_to_keep
        try:
            tokens_for_proposed_state = llm.get_num_tokens_from_messages(
                system_messages + block_to_add + messages_to_keep
            )
        except Exception:
            break

        # We reserve some space for the summary. keep_ratio defines how much of the limit to use for messages.
        if tokens_for_proposed_state <= max_tokens * keep_ratio:
            messages_to_keep = block_to_add + messages_to_keep
        else:
            # Always keep at least the most recent block if messages_to_keep is empty
            if not messages_to_keep and len(blocks) > 0:
                messages_to_keep = blocks[-1]
            break

    # Messages to be summarized are the ones not in messages_to_keep
    messages_to_summarize = [
        msg for msg in other_messages if msg not in messages_to_keep
    ]

    summary_message_str = ""
    if messages_to_summarize:
        logger.debug(f"Summarizing {len(messages_to_summarize)} older messages...")
        from core.llm_manager import get_fast_llm
        from langchain_core.messages import SystemMessage
        from langchain_core.prompts import ChatPromptTemplate

        summarizer_llm = get_fast_llm()
        if not summarizer_llm:
            logger.error(
                "❌ [LLM Utils] Fast LLM not available for summarization. Skipping summarization."
            )
        else:
            summarization_prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        "You are an expert at summarizing conversations. Summarize the following messages concisely, retaining the key information and context. The summary will be used to provide context to a language model.",
                    ),
                    (
                        "user",
                        "Please summarize these messages:\n\n{messages_to_summarize}",
                    ),
                ]
            )

            # Format messages for the prompt
            formatted_messages = "\n".join(
                [f"{msg.type}: {msg.content}" for msg in messages_to_summarize]
            )

            chain = summarization_prompt | summarizer_llm
            try:
                summary_response = await chain.ainvoke(
                    {"messages_to_summarize": formatted_messages}
                )
                summary_message_str = (
                    f"Summary of earlier conversation:\n{summary_response.content}"
                )
                logger.debug("✅ [LLM Utils] Summarization complete.")
            except Exception as e:
                logger.error(
                    f"❌ [LLM Utils] Error during summarization: {e}. Proceeding without summary."
                )

    # Construct the new message list
    final_messages: List[BaseMessage] = []
    final_messages.extend(system_messages)
    if summary_message_str:
        final_messages.append(SystemMessage(content=summary_message_str))
    final_messages.extend(messages_to_keep)

    # Final check
    try:
        final_tokens = llm.get_num_tokens_from_messages(final_messages)
    except Exception:
        final_tokens = max_tokens + 1

    if final_tokens > max_tokens:
        logger.warning(
            f"⚠️ [LLM Utils] Even after summarization, token count ({final_tokens}) exceeds limit ({max_tokens}). Further truncation may be needed."
        )
        # If still over, aggressively truncate and keep only system and last few messages
        if len(final_messages) > 3:
            final_messages = system_messages + final_messages[-2:]
            try:
                final_tokens = llm.get_num_tokens_from_messages(final_messages)
            except Exception:
                pass

    logger.debug(
        f"✅ [LLM Utils] Pruning complete. Messages reduced to {len(final_messages)} messages ({final_tokens} tokens)."
    )
    return final_messages
