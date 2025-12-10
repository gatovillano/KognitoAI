# core/prompt_manager.py

"""
Módulo para la Gestión Centralizada de Prompts.

Este módulo proporciona una clase, `PromptManager`, que se encarga de cargar,
gestionar y formatear todos los prompts utilizados por el agente de IA.
Centralizar la gestión de prompts aquí permite una mayor modularidad, facilita
las pruebas y simplifica la personalización y experimentación con nuevos prompts
sin alterar la lógica del agente.
"""

import logging
from typing import List, Optional, Dict, Any

from core.prompts import (
    KAI_SYSTEM_PROMPT,
    SUMMARIZATION_PROMPT,
    THREAD_TITLE_PROMPT,
    ENRICHED_PROMPT_TEMPLATE
)
from core.citation_models import CITATION_SYSTEM_PROMPT # Importar CITATION_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

class PromptManager:
    """
    Gestiona la carga, construcción y formato de los prompts del sistema.
    """
    def __init__(self, settings: Optional[Dict[str, Any]] = None):
        """
        Inicializa el gestor de prompts.

        Args:
            settings: Un diccionario de configuración (opcional) que puede
                      usarse para cargar configuraciones de prompts.
        """
        self.settings = settings or {}
        self.base_system_prompt = self.settings.get(
            "default_system_prompt", KAI_SYSTEM_PROMPT
        )
        logger.info("PromptManager inicializado.")

    def get_summarization_prompt(self) -> str:
        """
        Devuelve el prompt para la sumarización de historiales.
        """
        return SUMMARIZATION_PROMPT

    def get_thread_title_prompt(self) -> str:
        """
        Devuelve el prompt para la generación de títulos de hilos.
        """
        return THREAD_TITLE_PROMPT

    def get_enriched_prompt(self, knowledge_graph_context: str, user_message: str) -> str:
        """
        Construye un prompt enriquecido con contexto del Knowledge Graph.
        """
        return ENRICHED_PROMPT_TEMPLATE.format(
            knowledge_graph_context=knowledge_graph_context,
            user_message=user_message
        )

    def build_system_prompt(
        self,
        user_profile: Optional[Dict[str, Any]],
        relevant_memories: str,
        summary_string: str,
        custom_prompt_from_profile: Optional[str],
        workspace_prompt: Optional[str],
        tools: List[Any], # Añadir el parámetro tools
        account_id: str,
        telegram_id: Optional[int],
        mode: Optional[str] = None,
        user_message: str = "",
        has_explicit_rag_context: bool = False,
        explicit_document_names: Optional[List[str]] = None # Nuevo parámetro
    ) -> str:
        """
        Construye el prompt del sistema dinámicamente, integrando todos los
        componentes de contexto.
        """
        # Escape relevant_memories to prevent unescaped curly braces from causing KeyError
        # This ensures that any curly braces within the content are treated as literal characters
        # and not as placeholders for string formatting.
        escaped_relevant_memories = relevant_memories.replace('{', '{{').replace('}', '}}')

        # 1. Construir contexto del usuario
        profile_info = []
        if user_profile:
            if user_profile.nombre: profile_info.append(f"- Nombre: {user_profile.nombre}")
            if user_profile.gustos: profile_info.append(f"- Gustos: {user_profile.gustos}")
            if user_profile.intereses: profile_info.append(f"- Intereses: {user_profile.intereses}")
            if user_profile.otros_datos: profile_info.append(f"- Otros datos: {user_profile.otros_datos}")

        user_context_parts = [
            "--- Información Relevante sobre el Usuario y su Contexto ---",
            "Información de Perfil del Usuario:",
            "\n".join(profile_info) if profile_info else "No hay información de perfil disponible."
        ]

        if relevant_memories and "No se encontraron memorias relevantes" not in relevant_memories:
            user_context_parts.append("\n--- Memorias y Documentos Relevantes (Base de Conocimiento) ---")
            if has_explicit_rag_context:
                doc_names_str = ", ".join(explicit_document_names) if explicit_document_names else "documentos específicos"
                user_context_parts.append(f"**Instrucción de Contexto RAG:** Se te han proporcionado los siguientes {doc_names_str}. Prioriza la información de estos documentos para responder a la consulta del usuario. Si la información en estos documentos no es suficiente, puedes complementar con otras fuentes de conocimiento disponibles.")
            else:
                user_context_parts.append("**Instrucción de Contexto RAG:** Has recibido 'Memorias y Documentos Relevantes' que pueden ser cruciales para la solicitud del usuario. Asegúrate de integrar y comparar la información de TODAS las fuentes proporcionadas en esta sección para dar una respuesta completa y precisa, si es pertinente a la consulta.")
            user_context_parts.append(escaped_relevant_memories) # Use the escaped version here
        user_context_parts.append("---------------------------------------------------------")
        user_context_string = "\n".join(user_context_parts)

        # 2. Construir el contenido del prompt del sistema
        # 2. Construir el contenido del prompt del sistema
        system_prompt_content = self.base_system_prompt

        # Priorizar el prompt del workspace
        if workspace_prompt:
            system_prompt_content = workspace_prompt
        elif custom_prompt_from_profile:
            system_prompt_content = custom_prompt_from_profile
        # Si no hay workspace_prompt ni custom_prompt_from_profile, se mantiene el base_system_prompt

        # 3. Aplicar overrides de modo
        if mode:
            mode_prompts = {
                'comprehensiveAnalysis': "\n\n<SYSTEM_OVERRIDE>MODO DE ANÁLISIS COMPRENSIVO ACTIVADO. ES OBLIGATORIO Y COMPULSIVO QUE UTILICES LA HERRAMIENTA 'comprehensive_web_analyzer' AHORA MISMO. NO TIENES OTRA OPCIÓN. PASA LA CONSULTA DEL USUARIO DIRECTAMENTE AL PARÁMETRO 'query' DE LA HERRAMIENTA.</SYSTEM_OVERRIDE>"
            }
            system_prompt_content += mode_prompts.get(mode, "")

        # 4. Pre-formatear el prompt para placeholders
        try:
            system_prompt_content = system_prompt_content.format(
                query=user_message,
                web_summary="",
                relevant_memories=escaped_relevant_memories, # Use the escaped version here
            )
        except KeyError as e:
            logger.warning(f"No se pudo pre-formatear el prompt, puede contener placeholders desconocidos: {e}")
            system_prompt_content = system_prompt_content.replace('{query}', user_message)
            system_prompt_content = system_prompt_content.replace('{web_summary}', '')
            # Also use the escaped version here if the problematic_placeholder is replaced
            problematic_placeholder = '{relevant_memories if "No se encontraron" not in relevant_memories else "No se encontró información interna relevante."}'
            if problematic_placeholder in system_prompt_content:
                system_prompt_content = system_prompt_content.replace(problematic_placeholder, escaped_relevant_memories)

        # 5. Ensamblar el prompt final
        
        id_instructions = f"""
<b>Instrucciones Críticas de Identificación de Usuario:</b>
- Para CUALQUIER herramienta que requiera el argumento `account_id`, DEBES usar este valor exacto: <b>{account_id}</b>.
- Para CUALQUIER herramienta que requiera el argumento `telegram_id`, DEBES usar este valor exacto: <b>{telegram_id}</b>.
"""

        # Instrucciones específicas sobre herramientas disponibles
        tools_capabilities = """
<b>🌐 CAPACIDADES DE ACCESO A INTERNET Y HERRAMIENTAS DISPONIBLES:</b>

**IMPORTANTE: Tienes acceso COMPLETO a internet y a herramientas de búsqueda web.**

Herramientas de búsqueda disponibles:
- `web_search`: Busca información actualizada en internet usando Brave Search. Úsala cuando necesites información actual, noticias, datos recientes o cualquier información que no esté en tu conocimiento base.
- `web_scraper_tool`: Extrae contenido completo de URLs específicas.
- `comprehensive_web_analyzer`: Realiza análisis web profundo con múltiples búsquedas.

**REGLA CRÍTICA:** Cuando el usuario te pida buscar información en internet, investigar algo actual, o cualquier tarea que requiera datos actualizados:
1. **DEBES usar la herramienta `web_search`** inmediatamente
2. **NO digas que no tienes acceso a internet** - ¡SÍ LO TIENES!
3. **NO te disculpes por no poder buscar** - ¡SÍ PUEDES!
4. Simplemente ejecuta la búsqueda con los parámetros correctos

Ejemplo correcto de uso:
- Usuario: "Busca información sobre inteligencia artificial"
- Tú: [Llamas a web_search con query="inteligencia artificial"]

Ejemplo INCORRECTO:
- Usuario: "Busca información sobre inteligencia artificial"  
- Tú: "Lo siento, no tengo acceso a internet..." ❌ ¡NUNCA HAGAS ESTO!

Otras herramientas disponibles: gestión de notas, agenda, análisis de documentos, generación de imágenes, y más.
"""

        # 5. Ensamblar el prompt final
        final_prompt_parts = [
            user_context_string,
            summary_string,
            "<hr>",
            id_instructions,
            "<hr>",
            tools_capabilities,  # Nueva sección sobre herramientas
            "<hr>",
            "<b>Instrucción crítica:</b> Si necesitas usar herramientas, hazlo de una en una. Nunca intentes usar más de una herramienta en una sola respuesta. Espera la siguiente interacción antes de usar otra herramienta.",
            "<hr>",
            system_prompt_content,
            "<hr>",
            CITATION_SYSTEM_PROMPT, # Añadir las instrucciones de citación
        ]
        final_prompt = "\n".join(final_prompt_parts)
        logger.debug(f"DEBUG (PromptManager): Prompt final del sistema enviado al LLM:\n{final_prompt}") # Log para depuración
        return final_prompt


