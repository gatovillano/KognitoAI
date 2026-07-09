"""
Selector dinámico de herramientas relevantes para la consulta del usuario.
Reduce el tamaño del prompt y mejora la estabilidad de los LLMs.
"""

import logging
from typing import Any, List

logger = logging.getLogger(__name__)


def filter_relevant_tools(query: str, tools: List[Any], limit: int = 12) -> List[Any]:
    """
    Selecciona dinámicamente las herramientas más relevantes para la consulta del usuario.
    Esto reduce el tamaño del prompt y mejora la estabilidad de los LLMs.
    """
    if not query or not tools:
        return tools[:limit] if tools else []

    query_lower = query.lower()

    # 1. Herramientas Esenciales (Siempre incluidas)
    essential_names = {
        "web_search",
        "knowledge_graph",
        "deep_research",
        "web_scraper_tool",
        "comprehensive_web_analyzer",
    }

    # 2. Mapeo de Categorías de Intención
    category_map = {
        "notes": [
            "nota",
            "escribe",
            "recuerda",
            "apunta",
            "memoria",
            "note",
            "list_notes",
            "add_note",
        ],
        "documents": [
            "documento",
            "archivo",
            "pdf",
            "onlyoffice",
            "doc",
            "file",
            "create_document",
            "get_document",
        ],
        "calendar": [
            "evento",
            "reunion",
            "calendario",
            "cita",
            "hora",
            "agenda",
            "event",
            "schedule",
        ],
        "graph": ["grafo", "relacion", "conecta", "nodo", "mapa", "graph", "link"],
        "images": [
            "imagen",
            "foto",
            "dibuja",
            "genera",
            "image",
            "picture",
            "generate_image",
        ],
        "coding": [
            "codigo",
            "python",
            "script",
            "program",
            "terminal",
            "run",
            "execute",
        ],
    }

    selected_tools = []
    seen_names = set()

    # Prioridad 1: Esenciales
    for tool in tools:
        name = getattr(tool, "name", "").lower()
        if any(ess in name for ess in essential_names):
            selected_tools.append(tool)
            seen_names.add(name)

    # Prioridad 1.5: Skills de Usuario (Creadas dinámicamente)
    # Las favorecemos fuertemente para que el usuario vea el resultado de su creación.
    user_skills_added = 0
    for tool in tools:
        if len(selected_tools) >= limit:
            break
        if getattr(tool, "is_user_skill", False):
            name = getattr(tool, "name", "").lower()
            if name in seen_names:
                continue

            desc = getattr(tool, "description", "").lower()
            # Coincidencia o simplemente incluir si hay espacio y son pocas
            is_match = any(
                word in name or word in desc
                for word in query_lower.split()
                if len(word) > 3
            )

            if is_match or user_skills_added < 3:
                selected_tools.append(tool)
                seen_names.add(name)
                user_skills_added += 1
                logger.debug(
                    f"🌟 User Skill '{name}' seleccionada (match: {is_match})."
                )

    # Prioridad 2: Coincidencia de Palabras Clave de Categoría
    for cat, keywords in category_map.items():
        if any(kw in query_lower for kw in keywords):
            for tool in tools:
                name = getattr(tool, "name", "").lower()
                desc = getattr(tool, "description", "").lower()
                if name in seen_names:
                    continue

                # Si el nombre de la herramienta o su descripción coinciden con la categoría
                if any(kw in name for kw in keywords) or any(
                    kw in desc for kw in keywords
                ):
                    selected_tools.append(tool)
                    seen_names.add(name)

    # Prioridad 3: Coincidencia Semántica Simple (Palabras de la query en la descripción)
    query_words = [w for w in query_lower.split() if len(w) > 3]
    for tool in tools:
        if len(selected_tools) >= limit:
            break
        name = getattr(tool, "name", "").lower()
        if name in seen_names:
            continue

        desc = getattr(tool, "description", "").lower()
        if any(word in desc for word in query_words):
            selected_tools.append(tool)
            seen_names.add(name)

    # Relleno: Si faltan herramientas para llegar al límite, añadir las primeras disponibles
    if len(selected_tools) < 5:
        for tool in tools:
            if len(selected_tools) >= limit:
                break
            name = getattr(tool, "name", "").lower()
            if name not in seen_names:
                selected_tools.append(tool)
                seen_names.add(name)

    return selected_tools[:limit]
