# core/utils/llm_utils.py
import logging
from typing import List
from langchain_core.messages import AIMessage, MessageLikeRepresentation

logger = logging.getLogger(__name__)

def is_token_limit_exceeded(exception: Exception, model_name: str = None) -> bool:
    """Determine if an exception indicates a token/context limit was exceeded."""
    err_str = str(exception).lower()
    return "maximum context length" in err_str or "context_length_exceeded" in err_str

def remove_up_to_last_ai_message(messages: List[MessageLikeRepresentation]) -> List[MessageLikeRepresentation]:
    """Truncate message history by removing up to the last AI message."""
    for i in range(len(messages) - 1, -1, -1):
        if isinstance(messages[i], AIMessage):
            return messages[i + 1 :]
    return messages