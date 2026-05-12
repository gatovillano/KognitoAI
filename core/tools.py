# core/tools.py

"""
Módulo de Ensamblaje de Herramientas de LangChain.
Centraliza la carga de herramientas a través del SkillManager.
"""

import logging
from typing import List, Optional, Any
import asyncio

from langchain_core.tools import Tool
import uuid
from sqlalchemy import select
from core.database import SessionLocal, Account
from core.skill_manager import SkillManager
# from skills.html_generator_tool import HTMLGeneratorTool # REMOVED: Legacy import is now dynamic

# Configuración del logger para este módulo.
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mapa de palabras clave por categoría de skill.
# Se usa para decidir qué categorías instanciar según la consulta del usuario.
# Las categorías listadas en ALWAYS_ON_CATEGORIES (definidas en skill_manager)
# se cargan siempre y no necesitan aparecer aquí.
# ---------------------------------------------------------------------------
SKILL_CATEGORY_KEYWORDS: dict = {
    "calendar_skill": [
        "evento", "reunion", "reunión", "calendario", "cita", "hora", "agenda",
        "event", "schedule", "recordatorio", "reminder", "fecha", "date", "meeting",
    ],
    "notes_skill": [
        "nota", "notas", "escribe", "apunta", "anota", "note", "notes",
        "guarda", "apuntar", "ideas", "apuntame", "lista",
    ],
    "document_management_skill": [
        "documento", "documentos", "pdf", "archivo", "file", "doc",
        "crear documento", "create document", "report", "reporte",
    ],
    "rag_skill": [
        "busca en", "rag", "search document", "corpus", "base de conocimiento",
        "knowledge base", "documento", "pdf", "archivo adjunto",
    ],
    "data_and_forms_skill": [
        "tabla", "form", "formulario", "datos", "table", "stats",
        "prediction", "estadistica", "estadística", "data",
    ],
    "analysis_and_insights_skill": [
        "analiza", "insight", "analyze", "análisis", "analisis", "reporte",
        "report", "código", "codigo", "code", "historial",
    ],
    "media_and_generation_skill": [
        "imagen", "image", "genera", "generate", "foto", "photo",
        "dibujo", "mapa mental", "mindmap", "html", "diseña",
    ],
    "developer_tools_skill": [
        "código", "codigo", "python", "script", "github", "code",
        "repository", "repo", "file", "directory", "terminal",
    ],
    "onlyoffice_skill": [
        "office", "onlyoffice", "spreadsheet", "excel", "word",
        "presentacion", "presentación",
    ],
    "profile_and_tasks_skill": [
        "perfil", "tarea", "task", "profile", "contacto", "contact",
        "recordatorio", "reminder", "programa", "mis datos",
    ],
}


def select_relevant_categories(query: str, max_extra: int = 3) -> Optional[List[str]]:
    """
    Dado un query, retorna las categorías de skill relevantes para cargar.
    Siempre se añadirán las de ALWAYS_ON_CATEGORIES en skill_manager.
    Retorna None si no logra reducir (se cargarán todas).
    """
    if not query:
        return None

    query_lower = query.lower()
    scores: dict = {}
    for category, keywords in SKILL_CATEGORY_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in query_lower)
        if hits > 0:
            scores[category] = hits

    if not scores:
        return None  # sin hits → cargar todo

    # Ordenar por relevancia y tomar las top max_extra
    top_categories = sorted(scores, key=lambda c: scores[c], reverse=True)[:max_extra]
    logger.debug(f"📂 Categorías seleccionadas dinámicamente: {top_categories} (query: '{query[:60]}')")
    return top_categories

async def get_shared_dependencies():
    """
    Obtiene las instancias compartidas de GraphDB y GraphIntegration.
    Utilizado por herramientas que requieren acceso directo al grafo.
    """
    from core.agent import get_shared_graph_dependencies
    from knowledge_graph.graph_integration import GraphIntegration
    
    _graph_db, _ = await get_shared_graph_dependencies()
    if _graph_db:
        # Devolvemos la DB y una integración vinculada a esa DB
        return _graph_db, GraphIntegration(_graph_db)
    return None, None

async def get_all_langchain_tools(
    account_id: str,
    telegram_id: Optional[int] = None,
    thread_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    progress_callback: Optional[Any] = None,
    query: Optional[str] = None,
) -> List[Tool]:
    """
    Recoge, instancia y devuelve una lista de todas las herramientas LangChain habilitadas
    descubiertas por el SkillManager.
    """
    logger.debug("⚙️ Assembling agent toolbox via SkillManager...")

    # Selección dinámica de categorías (DESACTIVADA por preferencia del usuario)
    relevant_categories = None
    logger.info("🗂️ Carga completa de todas las categorías de skills (filtro dinámico desactivado).")


    
    # Fetch disabled skills for this user
    disabled_skills = []
    try:
        async with SessionLocal() as db:
            account = await db.get(Account, uuid.UUID(account_id))
            if account:
                disabled_skills = account.disabled_skills or []
    except Exception as e:
        logger.warning(f"Could not fetch disabled_skills for account {account_id}: {e}")

    workspace_name = None
    try:
        if workspace_id:
            from core.database import Workspace
            async with SessionLocal() as db:
                stmt = select(Workspace).where(Workspace.id == uuid.UUID(workspace_id))
                result = await db.execute(stmt)
                workspace_obj = result.scalar_one_or_none()
                if workspace_obj:
                    workspace_name = workspace_obj.name
    except Exception as e:
        logger.warning(f"Could not fetch workspace_name for workspace_id {workspace_id}: {e}")

    try:
        from core.skill_manager import get_skill_manager
        skill_manager = get_skill_manager()
        
        # El SkillManager maneja la inicialización de dependencias compartidas (Neo4j, etc)
        # y la inyección de account_id, workspace_id, etc.
        tools = await skill_manager.load_skills(
            account_id=account_id,
            telegram_id=telegram_id,
            thread_id=thread_id,
            workspace_id=workspace_id,
            workspace_name=workspace_name,
            progress_callback=progress_callback,
            disabled_skills=disabled_skills,
            relevant_categories=relevant_categories,
        )
        
        # --- Lógica Especial para Herramientas Compuestas ---
        # Si alguna herramienta necesita a otra como dependencia (ej: DeepResearchTool),
        # podemos hacer una inyección cruzada aquí.
        
        deep_research_tool = next((t for t in tools if getattr(t, "name", None) == "deep_research"), None)
        if deep_research_tool:
             # El nuevo DeepResearchTool descubierto dinámicamente puede necesitar configurar
             # sus referencias internas si no las resuelve por sí mismo al compilar su grafo.
             pass

        # Deduplicación por nombre por seguridad
        final_tools: List[Tool] = []
        seen_names = set()
        for tool in tools:
            if tool.name not in seen_names:
                final_tools.append(tool)
                seen_names.add(tool.name)
            else:
                logger.warning(f"Duplicate tool '{tool.name}' ignored during assembly.")

        logger.info(f"--- 🧰 Toolbox Assembled ({len(final_tools)} dynamic skills) ---")
        return final_tools

    except Exception as e:
        logger.error(f"❌ Critical error assembling toolbox: {e}", exc_info=True)
        return []