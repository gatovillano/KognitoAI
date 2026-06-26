import pytest
import re
import asyncio
from unittest.mock import MagicMock
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from api.chat import Message
from core.pty_sessions import create_session, get_session, close_session

def test_content_parts_reconstruction():
    # Simular final_messages de un agente
    tool_call_id = "call_123"
    
    # 1. HumanMessage del usuario
    human_msg = HumanMessage(content="Ejecuta ls en la terminal")
    
    # 2. AIMessage iniciando la llamada a la herramienta
    ai_call_msg = AIMessage(
        content="",
        tool_calls=[{
            "name": "terminal_executor",
            "args": {"command": "ls"},
            "id": tool_call_id
        }]
    )
    
    # 3. ToolMessage con el output de la terminal y data-session-id
    tool_response_msg = ToolMessage(
        content='<div data-session-id="session_xyz_789">Directorio: file.txt</div>',
        tool_call_id=tool_call_id
    )
    
    # 4. AIMessage final de respuesta
    final_ai_msg = AIMessage(
        content="He listado el directorio.",
        additional_kwargs={}
    )
    
    final_messages = [human_msg, ai_call_msg, tool_response_msg, final_ai_msg]
    
    # Replicar la lógica implementada
    ai_content_parts = []
    
    last_human_idx = -1
    for idx in range(len(final_messages) - 1, -1, -1):
        if isinstance(final_messages[idx], HumanMessage):
            last_human_idx = idx
            break
            
    assert last_human_idx == 0
    
    intermediate_messages = final_messages[last_human_idx + 1 : -1]
    assert len(intermediate_messages) == 2
    
    tool_results = {}
    for msg in intermediate_messages:
        if isinstance(msg, ToolMessage):
            tool_results[msg.tool_call_id] = msg
            
    assert tool_call_id in tool_results
    
    for msg in intermediate_messages:
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for tool_call in msg.tool_calls:
                t_call_id = tool_call.get("id")
                tool_name = tool_call.get("name")
                
                tool_msg = tool_results.get(t_call_id)
                status = "end"
                content = f"Usando {tool_name}..."
                pty_session = None
                
                if tool_msg:
                    content = str(tool_msg.content)
                    if tool_name == "terminal_executor":
                        match = re.search(r'data-session-id="([^"]+)"', content)
                        if match:
                            pty_session = {"session_id": match.group(1)}
                else:
                    status = "error"
                    
                ai_content_parts.append({
                    "type": "tool_call",
                    "content": content,
                    "tool_name": tool_name,
                    "status": status,
                    "pty_session": pty_session,
                    "id": t_call_id
                })
                
    # Extraer texto final del AI
    ai_content_parts.append({
        "type": "text",
        "content": final_ai_msg.content
    })
    
    assert len(ai_content_parts) == 2
    assert ai_content_parts[0]["type"] == "tool_call"
    assert ai_content_parts[0]["pty_session"] == {"session_id": "session_xyz_789"}
    assert ai_content_parts[0]["status"] == "end"
    assert ai_content_parts[1]["type"] == "text"
    assert ai_content_parts[1]["content"] == "He listado el directorio."

@pytest.mark.anyio
async def test_pty_session_history_and_delay():
    import uuid
    account_id = str(uuid.uuid4())
    # 1. Crear una sesión que imprima algo y termine
    session_id = await create_session(
        command="echo 'hello terminal persistence'",
        account_id=account_id,
    )
    
    # 2. Recuperar la sesión
    session = get_session(session_id)
    assert session is not None
    assert session["account_id"] == account_id
    assert not session["closed"]
    
    # 3. Esperar a que el proceso termine usando close_event
    close_event = session.get("close_event")
    assert close_event is not None
    
    await asyncio.wait_for(close_event.wait(), timeout=5.0)
    
    # 4. Verificar que esté cerrada, pero que la sesión SIGA en _sessions (delayed pop)
    assert session["closed"]
    
    session_after_close = get_session(session_id)
    assert session_after_close is not None
    
    # Verificar que haya acumulado la salida
    accumulated = session_after_close.get("accumulated_output", [])
    assert len(accumulated) > 0
    full_output = "".join(accumulated)
    assert "hello terminal persistence" in full_output
    
    # 5. Limpieza explícita
    await close_session(session_id)
    assert get_session(session_id) is None
