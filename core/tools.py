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

# Configuración del logger para este módulo.
logger = logging.getLogger(__name__)

async def get_all_langchain_tools(
    account_id: str,
    telegram_id: Optional[int] = None,
    thread_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    progress_callback: Optional[Any] = None
) -> List[Tool]:
    """
    Recoge, instancia y devuelve una lista de todas las herramientas LangChain habilitadas
    descubiertas por el SkillManager.
    """
    logger.debug("⚙️ Assembling agent toolbox via SkillManager...")
    
    # Fetch disabled skills for this user
    disabled_skills = []
    try:
        async with SessionLocal() as db:
            account = await db.get(Account, uuid.UUID(account_id))
            if account:
                disabled_skills = account.disabled_skills or []
    except Exception as e:
        logger.warning(f"Could not fetch disabled_skills for account {account_id}: {e}")

    try:
        skill_manager = SkillManager()
        
        # El SkillManager maneja la inicialización de dependencias compartidas (Neo4j, etc)
        # y la inyección de account_id, workspace_id, etc.
        tools = await skill_manager.load_skills(
            account_id=account_id,
            telegram_id=telegram_id,
            thread_id=thread_id,
            workspace_id=workspace_id,
            progress_callback=progress_callback,
            disabled_skills=disabled_skills
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