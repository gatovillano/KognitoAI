"""
KognitoAI Model Context Protocol (MCP) Server.
Expone el ecosistema de herramientas, memorias, grafos de conocimiento
y habilidades de KognitoAI para que cualquier agente externo (Claude Desktop, Cursor,
Windsurf, Antigravity, Fito, etc.) pueda interactuar fluidamente con la plataforma.
"""

import sys
import os
import json
import logging
import asyncio
import threading
from typing import Dict, Any, List, Optional

# Asegurar path raíz del proyecto KognitoAI
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from mcp.server.lowlevel import Server
from mcp.types import (
    Tool as MCPTool,
    TextContent,
    Resource,
    Prompt,
    PromptMessage,
    PromptArgument,
    GetPromptResult,
)
import mcp.server.stdio

from core.database import SessionLocal, Account

# Configurar logger exclusivamente hacia sys.stderr (stdio está reservado para JSON-RPC)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - [%(levelname)s] - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("kognito_mcp_server")

# Default account_id de KognitoAI si no se especifica en env
DEFAULT_ACCOUNT_ID = os.environ.get("KOGNITO_ACCOUNT_ID", "5b8d59b0-69b7-4aa8-9bb0-bf07511222a6")
DEFAULT_WORKSPACE_ID = os.environ.get("KOGNITO_WORKSPACE_ID", None)

server = Server("kognito-ai")

# Cache global de herramientas cargadas
_cached_tools: Dict[str, Any] = {}
_tools_loaded = False
_loading_in_progress = False

# Herramientas excluidas por seguridad
EXCLUDED_TOOLS = {"terminal_executor", "terminal_executor_skill", "host_terminal_skill"}


def _background_loader_worker(account_id: str, workspace_id: Optional[str]):
    """Carga las herramientas en un hilo independiente para NO bloquear el event loop de asyncio ni el handshake."""
    global _cached_tools, _tools_loaded, _loading_in_progress
    logger.info(f"Iniciando carga de herramientas KognitoAI en segundo plano para account_id: {account_id}...")
    try:
        # Importaciones diferidas dentro del hilo
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        from core.skill_manager import get_skill_manager
        skill_manager = get_skill_manager()
        
        tools = loop.run_until_complete(skill_manager.load_skills(
            account_id=account_id,
            workspace_id=workspace_id,
        ))
        loop.close()

        seen = {}
        for t in tools:
            if t.name in EXCLUDED_TOOLS:
                continue
            if t.name not in seen:
                seen[t.name] = t

        _cached_tools.update(seen)
        _tools_loaded = True
        logger.info(f"✅ Carga en background completa: {len(_cached_tools)} herramientas KognitoAI disponibles.")
    except Exception as e:
        logger.error(f"❌ Error al cargar herramientas en segundo plano: {e}", exc_info=True)
    finally:
        _loading_in_progress = False


def trigger_background_loader():
    global _loading_in_progress
    if _tools_loaded or _loading_in_progress:
        return
    _loading_in_progress = True
    t = threading.Thread(
        target=_background_loader_worker,
        args=(DEFAULT_ACCOUNT_ID, DEFAULT_WORKSPACE_ID),
        daemon=True,
        name="KognitoToolLoader"
    )
    t.start()


def langchain_tool_to_mcp(tool: Any) -> MCPTool:
    """Convierte un objeto Tool de LangChain a la especificación de MCPTool."""
    schema = {}
    if hasattr(tool, "args_schema") and tool.args_schema:
        try:
            if hasattr(tool.args_schema, "model_json_schema"):
                schema = tool.args_schema.model_json_schema()
            elif hasattr(tool.args_schema, "schema"):
                schema = tool.args_schema.schema()
        except Exception as err:
            logger.warning(f"No se pudo extraer schema formal para {tool.name}: {err}")

    properties = schema.get("properties", {})
    required = schema.get("required", [])

    clean_schema = {
        "type": "object",
        "properties": properties,
    }
    if required:
        clean_schema["required"] = required

    description = tool.description or f"Herramienta KognitoAI: {tool.name}"

    return MCPTool(
        name=tool.name,
        description=description,
        inputSchema=clean_schema,
    )


# ==============================================================================
# MANEJADORES DE HERRAMIENTAS (TOOLS)
# ==============================================================================

@server.list_tools()
async def handle_list_tools() -> List[MCPTool]:
    """Retorna la lista de herramientas disponibles inmediatamente en <10ms."""
    trigger_background_loader()

    mcp_tool_list = []
    seen = set()

    # 1. Si tenemos herramientas en caché cargadas dinámicamente, usarlas
    if _cached_tools:
        for tool in list(_cached_tools.values()):
            name = getattr(tool, "name", "")
            if name in EXCLUDED_TOOLS or name in seen:
                continue
            seen.add(name)
            try:
                mcp_tool_list.append(langchain_tool_to_mcp(tool))
            except Exception as e:
                logger.error(f"Error convirtiendo herramienta {name}: {e}")

    # 2. Si aún están cargándose en background, servir inmediatamente el snapshot persistido
    if not mcp_tool_list:
        cache_path = os.path.join(os.path.dirname(__file__), "tools_cache.json")
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    cached_definitions = json.load(f)
                    for item in cached_definitions:
                        if item["name"] not in EXCLUDED_TOOLS and item["name"] not in seen:
                            seen.add(item["name"])
                            mcp_tool_list.append(
                                MCPTool(
                                    name=item["name"],
                                    description=item.get("description", ""),
                                    inputSchema=item.get("inputSchema", {"type": "object"})
                                )
                            )
            except Exception as e:
                logger.warning(f"No se pudo leer tools_cache.json: {e}")

    # Añadir herramienta especial para consulta directa a KAI (Agente Completo)
    mcp_tool_list.append(
        MCPTool(
            name="kai_chat",
            description=(
                "Interactúa directamente con KAI, el asistente principal de inteligencia aumentada "
                "de KognitoAI. Ejecuta razonamiento, orquestación, memoria y herramientas en contexto."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "El mensaje o consulta que deseas enviar a KAI."
                    },
                    "thread_id": {
                        "type": "string",
                        "description": "ID opcional del hilo de conversación para continuar contexto."
                    }
                },
                "required": ["message"]
            }
        )
    )

    return mcp_tool_list


@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Ejecuta una herramienta de KognitoAI solicitada por un agente externo."""
    trigger_background_loader()
    
    # Esperar si el loader aún está terminando de procesar la herramienta solicitada
    if name != "kai_chat" and name not in _cached_tools and not _tools_loaded:
        for _ in range(50):
            if name in _cached_tools or _tools_loaded:
                break
            await asyncio.sleep(0.1)

    if name in EXCLUDED_TOOLS:
        return [
            TextContent(
                type="text",
                text=f"Error: La herramienta '{name}' está deshabilitada en el servidor MCP por motivos de seguridad."
            )
        ]

    # Invocación directa al Agente KAI
    if name == "kai_chat":
        message = arguments.get("message", "")
        thread_id = arguments.get("thread_id", None)
        try:
            from core.agent import get_agent_response
            response = await get_agent_response(
                message=message,
                account_id=DEFAULT_ACCOUNT_ID,
                thread_id=thread_id,
                workspace_id=DEFAULT_WORKSPACE_ID,
            )
            return [TextContent(type="text", text=str(response))]
        except Exception as e:
            logger.error(f"Error al invocar kai_chat: {e}", exc_info=True)
            return [TextContent(type="text", text=f"Error al procesar solicitud con KAI: {str(e)}")]

    # Invocación a herramienta de LangChain en caché
    tool = _cached_tools.get(name)
    if not tool:
        return [
            TextContent(
                type="text",
                text=f"Error: La herramienta '{name}' no fue encontrada en KognitoAI."
            )
        ]

    try:
        # Inyectar account_id si la herramienta lo admite y no vino en los argumentos
        clean_args = dict(arguments or {})
        if hasattr(tool, "args_schema") and tool.args_schema:
            schema_fields = getattr(tool.args_schema, "__fields__", {}) or getattr(tool.args_schema, "model_fields", {})
            if "account_id" in schema_fields and "account_id" not in clean_args:
                clean_args["account_id"] = DEFAULT_ACCOUNT_ID
            if "workspace_id" in schema_fields and "workspace_id" not in clean_args and DEFAULT_WORKSPACE_ID:
                clean_args["workspace_id"] = DEFAULT_WORKSPACE_ID

        # Ejecución síncrona o asíncrona según soporte de la herramienta
        if hasattr(tool, "ainvoke"):
            result = await tool.ainvoke(clean_args)
        elif hasattr(tool, "_arun"):
            result = await tool._arun(**clean_args)
        elif hasattr(tool, "invoke"):
            result = tool.invoke(clean_args)
        elif hasattr(tool, "_run"):
            result = tool._run(**clean_args)
        elif callable(tool):
            result = tool(**clean_args)
        else:
            raise RuntimeError(f"La herramienta {name} no tiene un método de ejecución reconocido.")

        # Normalizar respuesta a texto
        if isinstance(result, (dict, list)):
            text_result = json.dumps(result, ensure_ascii=False, indent=2)
        else:
            text_result = str(result)

        return [TextContent(type="text", text=text_result)]
    except Exception as e:
        logger.error(f"Error ejecutando herramienta {name}: {e}", exc_info=True)
        return [
            TextContent(
                type="text",
                text=f"Error ejecutando {name}: {str(e)}"
            )
        ]


# ==============================================================================
# MANEJADORES DE RECURSOS (RESOURCES)
# ==============================================================================

@server.list_resources()
async def handle_list_resources() -> List[Resource]:
    """Lista recursos de datos consultables de KognitoAI."""
    return [
        Resource(
            uri="kognito://system/status",
            name="Estado del Sistema KognitoAI",
            description="Información de salud, base de datos y estado general de KognitoAI.",
            mimeType="application/json",
        ),
        Resource(
            uri="kognito://account/info",
            name="Información de la Cuenta Activa",
            description="Detalles de la cuenta de usuario configurada para esta sesión MCP.",
            mimeType="application/json",
        ),
    ]


@server.read_resource()
async def handle_read_resource(uri: str) -> str:
    """Lee el contenido de un recurso solicitado."""
    if uri == "kognito://system/status":
        status_data = {
            "status": "online",
            "platform": "KognitoAI",
            "active_account_id": DEFAULT_ACCOUNT_ID,
            "tools_loaded_count": len(_cached_tools),
            "tools_ready": _tools_loaded,
        }
        return json.dumps(status_data, indent=2)

    elif uri == "kognito://account/info":
        info = {
            "account_id": DEFAULT_ACCOUNT_ID,
            "workspace_id": DEFAULT_WORKSPACE_ID,
        }
        try:
            with SessionLocal() as db:
                acc = db.query(Account).filter(Account.id == DEFAULT_ACCOUNT_ID).first()
                if acc:
                    info["name"] = getattr(acc, "name", "Desconocido")
                    info["email"] = getattr(acc, "email", "Desconocido")
        except Exception as e:
            info["db_error"] = str(e)
        return json.dumps(info, indent=2)

    raise ValueError(f"Recurso no encontrado: {uri}")


# ==============================================================================
# MANEJADORES DE PROMPTS
# ==============================================================================

@server.list_prompts()
async def handle_list_prompts() -> List[Prompt]:
    """Lista las plantillas de prompts guiadas de KognitoAI."""
    return [
        Prompt(
            name="kognito-research-assistant",
            description="Prompt guiado para activar a KAI como investigador cognitivo en un tema específico.",
            arguments=[
                PromptArgument(
                    name="topic",
                    description="Tema a investigar con KognitoAI",
                    required=True,
                )
            ],
        )
    ]


@server.get_prompt()
async def handle_get_prompt(name: str, arguments: Dict[str, str]) -> GetPromptResult:
    """Devuelve la estructura del prompt solicitado."""
    if name == "kognito-research-assistant":
        topic = arguments.get("topic", "conocimiento general")
        text = (
            f"Eres un co-investigador conectado a KognitoAI para investigar: '{topic}'.\n"
            "Tienes acceso completo a la base de conocimiento, documentos, grafos de memoria "
            "y herramientas de KognitoAI mediante las funciones provistas en este servidor MCP.\n"
            "Utiliza las herramientas 'knowledge_search', 'query_memory_graph' o 'deep_research' según corresponda."
        )
        return GetPromptResult(
            description=f"Asistente KognitoAI para {topic}",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(type="text", text=text)
                )
            ]
        )
    raise ValueError(f"Prompt '{name}' no existe.")


# ==============================================================================
# PUNTO DE ENTRADA STDIO
# ==============================================================================

async def main():
    logger.info("Iniciando servidor MCP KognitoAI en modo STDIO...")
    # Disparar cargador en background en thread independiente para no bloquear el loop
    trigger_background_loader()

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )

if __name__ == "__main__":
    asyncio.run(main())
