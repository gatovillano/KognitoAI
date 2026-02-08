import json
import logging
import re
from typing import List, Any, Sequence, cast
from langchain_core.messages import AIMessage, BaseMessage, MessageLikeRepresentation, ToolMessage, HumanMessage
from langchain_core.language_models import BaseChatModel # Import BaseChatModel
from langchain_core.runnables import Runnable

logger = logging.getLogger(__name__)

async def invoke_structured_output(llm: BaseChatModel, schema: Any, prompt: str, retry_config: dict = None) -> Any:
    """Invokes an LLM with structured output, falling back to manual JSON parsing if needed."""
    try:
        # 1. Intentar con el método estándar (herramientas)
        model = llm.with_structured_output(schema)
        if retry_config:
            model = model.with_retry(**retry_config)
        return await model.ainvoke([HumanMessage(content=prompt)])
    except Exception as e:
        error_str = str(e)
        logger.warning(f"⚠️ [Structured Output] Standard structured output method failed: {e}. Attempting manual JSON parsing fallback.")

        # Manual parsing logic (moved here as the ultimate fallback)
        schema_definition = schema.schema() if hasattr(schema, 'schema') else {}
        schema_json = json.dumps(schema_definition, indent=2)

        # Crear un ejemplo dinámico para guiar al LLM
        example = {}
        if schema_definition and 'properties' in schema_definition:
            for prop, details in schema_definition['properties'].items():
                prop_type = details.get('type')
                description = details.get('description', f'un valor para {prop}')
                if prop_type == 'string':
                    example[prop] = f"Un valor de tipo string que representa {description}"
                elif prop_type == 'boolean':
                    example[prop] = False
                elif prop_type == 'integer' or prop_type == 'number':
                    example[prop] = 0
                elif prop_type == 'array':
                    example[prop] = []
                else:
                    example[prop] = "..."
        
        example_json = json.dumps(example, indent=2, ensure_ascii=False)

        manual_prompt = (
            f"{prompt}\n\n"
            f"IMPORTANTE: Tu respuesta DEBE ser únicamente un objeto JSON válido que se ajuste al siguiente esquema. No incluyas ninguna otra explicación, texto introductorio o markdown.\n\n"
            f"Esquema JSON requerido:\n{schema_json}\n\n"
            f"Ejemplo de un objeto JSON con el formato correcto:\n{example_json}\n\n"
            f"Ahora, basándote en la conversación, genera el objeto JSON final:"
        )
        
        response = await llm.ainvoke([HumanMessage(content=manual_prompt)])
        
        content = response.content if hasattr(response, 'content') else str(response)
        # Intentar extraer JSON de la respuesta
        json_match = re.search(r'(\{.*\})', content, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                # Usar parse_obj si está disponible (Pydantic V2), si no, usar el constructor
                if hasattr(schema, 'parse_obj'):
                    return schema.parse_obj(data)
                # Pydantic V1/V2 __init__
                return schema(**data)
            except Exception as e3:
                logger.error(f"❌ [Structured Output] Manual parsing failed: {e3}")
                raise e3
        else:
            logger.error(f"❌ [Structured Output] No JSON found in response after manual prompting.")
            raise ValueError("No valid JSON found in response after manual prompting")



def is_token_limit_exceeded(exception: Exception, model_name: str = None) -> bool:
    """Determine if an exception indicates a token/context limit was exceeded."""
    err_str = str(exception).lower()
    return "maximum context length" in err_str or "context_length_exceeded" in err_str

def remove_up_to_last_ai_message(messages: List[MessageLikeRepresentation]) -> List[MessageLikeRepresentation]:
    """Truncate message history by removing up to the last AI message (and its tool outputs if any)."""
    for i in range(len(messages) - 1, -1, -1):
        msg = messages[i]
        if isinstance(msg, AIMessage):
            # Found the last AI message.
            # If it has tool calls, we must also skip the subsequent ToolMessages to avoid orphan tool outputs.
            start_index = i + 1
            if msg.tool_calls:
                while start_index < len(messages) and isinstance(messages[start_index], ToolMessage):
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

    logger.warning(f"⚠️ [LLM Utils] Message history ({current_tokens} tokens) exceeds max_tokens ({max_tokens} tokens). Pruning and summarizing...")

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
            while i < len(other_messages) and isinstance(other_messages[i], ToolMessage):
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
            tokens_for_proposed_state = llm.get_num_tokens_from_messages(system_messages + block_to_add + messages_to_keep)
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
    messages_to_summarize = [msg for msg in other_messages if msg not in messages_to_keep]

    summary_message_str = ""
    if messages_to_summarize:
        logger.info(f"Summarizing {len(messages_to_summarize)} older messages...")
        from core.llm_manager import get_fast_llm
        from langchain_core.messages import SystemMessage
        from langchain_core.prompts import ChatPromptTemplate

        summarizer_llm = get_fast_llm()
        if not summarizer_llm:
            logger.error("❌ [LLM Utils] Fast LLM not available for summarization. Skipping summarization.")
        else:
            summarization_prompt = ChatPromptTemplate.from_messages([
                ("system", "You are an expert at summarizing conversations. Summarize the following messages concisely, retaining the key information and context. The summary will be used to provide context to a language model."),
                ("user", "Please summarize these messages:\n\n{messages_to_summarize}")
            ])
            
            # Format messages for the prompt
            formatted_messages = "\n".join([f"{msg.type}: {msg.content}" for msg in messages_to_summarize])
            
            chain = summarization_prompt | summarizer_llm
            try:
                summary_response = await chain.ainvoke({"messages_to_summarize": formatted_messages})
                summary_message_str = f"Summary of earlier conversation:\n{summary_response.content}"
                logger.info("✅ [LLM Utils] Summarization complete.")
            except Exception as e:
                logger.error(f"❌ [LLM Utils] Error during summarization: {e}. Proceeding without summary.")

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
        logger.warning(f"⚠️ [LLM Utils] Even after summarization, token count ({final_tokens}) exceeds limit ({max_tokens}). Further truncation may be needed.")
        # If still over, aggressively truncate and keep only system and last few messages
        if len(final_messages) > 3:
            final_messages = system_messages + final_messages[-2:]
            try:
                final_tokens = llm.get_num_tokens_from_messages(final_messages)
            except Exception:
                pass
    
    logger.info(f"✅ [LLM Utils] Pruning complete. Messages reduced to {len(final_messages)} messages ({final_tokens} tokens).")
    return final_messages