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
    ENRICHED_PROMPT_TEMPLATE,
    HTML_DESIGN_PROMPT,
    TELEGRAM_FORMATTING_PROMPT
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
        explicit_document_names: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None # Nuevo parámetro
    ) -> str:
        """
        Construye el prompt del sistema dinámicamente, integrando todos los
        componentes de contexto.
        """
        # 0. Construir instrucciones de contexto específico
        context_instructions = ""
        if context:
            ctx_type = context.get("type")
            ctx_id = context.get("id")
            ctx_snapshot = context.get("snapshot", {})
            
            if ctx_type == "table":
                context_instructions = f"""
--- CONTEXTO DE TABLA ACTIVA ---
Estás asistiendo al usuario en la vista de la tabla '{ctx_snapshot.get('name', 'Sin nombre')}'.
ID de la Tabla: {ctx_id}
Columnas: {ctx_snapshot.get('columns', [])}
Instrucción: Tienes acceso a herramientas de análisis de tablas. Si el usuario pregunta sobre estos datos, usa `get_table_stats` o `get_table_prediction` si es necesario, o simplemente analiza el snapshot proporcionado.
-------------------------------
"""
            elif ctx_type == "graph":
                context_instructions = f"""
--- CONTEXTO DE GRAFO ACTIVO ---
El usuario está explorando un Grafo de Conocimiento.
ID del Grafo/Colección: {ctx_id}
Instrucción: Prioriza el uso de `knowledge_graph_tool` para realizar consultas Cypher y explicar las relaciones entre entidades.
-------------------------------
"""
            elif ctx_type == "analysis":
                # Extraer contenido detallado del análisis si está disponible en el snapshot
                analysis_result = ctx_snapshot.get("result", {}) if isinstance(ctx_snapshot.get("result"), dict) else ctx_snapshot
                
                content_parts = []
                
                # 1. Título y Resumen
                title = ctx_snapshot.get('title') or analysis_result.get('title') or 'Sin título'
                summary = analysis_result.get('summary') or ctx_snapshot.get('summary')
                if summary:
                    content_parts.append(f"RESUMEN EJECUTIVO:\n{summary}")
                
                # 2. Hallazgos (Findings)
                findings = analysis_result.get('findings') or ctx_snapshot.get('findings')
                if findings:
                    if isinstance(findings, list):
                        findings_text = "\n".join([f"- {f}" for f in findings])
                    else:
                        findings_text = str(findings)
                    content_parts.append(f"HALLAZGOS CLAVE:\n{findings_text}")
                
                # 3. Reporte Final (el más importante)
                final_report = analysis_result.get('final_report') or ctx_snapshot.get('final_report')
                if final_report:
                    content_parts.append(f"INFORME DETALLADO:\n{final_report}")
                
                # 4. Recomendaciones
                recommendations = analysis_result.get('recommendations') or ctx_snapshot.get('recommendations')
                if recommendations:
                    if isinstance(recommendations, list):
                        rec_text = "\n".join([f"- {r}" for r in recommendations])
                    else:
                        rec_text = str(recommendations)
                    content_parts.append(f"ACCIONES Y RECOMENDACIONES:\n{rec_text}")

                analysis_content = "\n\n".join(content_parts) if content_parts else "No se pudo extraer el contenido detallado del informe."

                context_instructions = f"""
--- CONTEXTO DE ANÁLISIS ACTIVO ---
El usuario está revisando el informe de análisis: '{title}'.

CONTENIDO DEL INFORME:
{analysis_content}

Instrucción: Ayuda al usuario a interpretar los hallazgos de este análisis detallado arriba. Responde preguntas basadas en esta información. No inventes datos que no estén en el informe. Si el usuario pide más detalle sobre algo no cubierto, puedes ofrecerte a realizar una nueva búsqueda web específica.
-------------------------------
"""
            elif ctx_type == "collection":
                context_instructions = f"""
--- CONTEXTO DE COLECCIÓN ACTIVA ---
Estás asistiendo al usuario en la vista de la colección '{ctx_snapshot.get('name', 'Sin nombre')}'.
ID de la Colección: {ctx_id}
Documentos: {ctx_snapshot.get('document_count', 0)}
Instrucción: El usuario está interesado en la información contenida en esta colección. Prioriza el uso de herramientas de búsqueda en documentos (RAG) filtrando por esta colección si es posible, o simplemente utiliza el conocimiento que ya tienes sobre ella.
------------------------------------
"""

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
            doc_names_str = ", ".join(explicit_document_names) if explicit_document_names else "documentos específicos"
            rag_instruction = (
                f"**Instrucción de Contexto RAG:** Se te han proporcionado los siguientes {doc_names_str}. "
                "Prioriza la información de estos documentos para responder a la consulta del usuario. "
                "Si la información en estos documentos no es suficiente, puedes complementar con otras fuentes de conocimiento disponibles."
                if has_explicit_rag_context
                else "**Instrucción de Contexto RAG:** Has recibido 'Memorias y Documentos Relevantes' que pueden ser cruciales para la solicitud del usuario. "
                "Asegúrate de integrar y comparar la información de TODAS las fuentes proporcionadas en esta sección para dar una respuesta completa y precisa, si es pertinente a la consulta."
            )
            user_context_parts.extend([
                "\n--- Memorias y Documentos Relevantes (Base de Conocimiento) ---",
                rag_instruction,
                relevant_memories
            ])
        user_context_parts.append("---------------------------------------------------------")
        user_context_string = "\n".join(user_context_parts)

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
                relevant_memories=relevant_memories,
            )
        except KeyError as e:
            logger.warning(f"No se pudo pre-formatear el prompt, puede contener placeholders desconocidos: {e}")
            system_prompt_content = system_prompt_content.replace('{query}', user_message)
            system_prompt_content = system_prompt_content.replace('{web_summary}', '')
            # Also use the escaped version here if the problematic_placeholder is replaced
            problematic_placeholder = '{relevant_memories if "No se encontraron" not in relevant_memories else "No se encontró información interna relevante."}'
            if problematic_placeholder in system_prompt_content:
                system_prompt_content = system_prompt_content.replace(problematic_placeholder, relevant_memories)

        # 5. Ensamblar el prompt final
        
        id_instructions = f"""
<b>Instrucciones Críticas de Identificación de Usuario:</b>
- Para CUALQUIER herramienta que requiera el argumento `account_id`, DEBES usar este valor exacto: <b>{account_id}</b>.
- Para CUALQUIER herramienta que requiera el argumento `telegram_id`, DEBES usar este valor exacto: <b>{telegram_id}</b>.
"""

        # Instrucciones específicas sobre herramientas disponibles (más concisas)
        tools_capabilities = """
<b>🌐 CAPACIDADES Y HERRAMIENTAS:</b>

**Acceso a Internet:** Tienes acceso completo a internet. Usa `web_search` para información actual.
**Regla Crítica:** Si el usuario pide buscar, **DEBES usar `web_search`**. Nunca digas que no puedes buscar.

Herramientas clave:
- `web_search(query: str)`: Búsqueda web con Brave Search.
- `web_scraper_tool(url: str)`: Extrae contenido de URLs.
- `comprehensive_web_analyzer(query: str)`: Análisis web profundo.
- `deep_research(query: str)`: Investigación profunda multi-agente. Ideal para temas complejos que requieren reportes narrativos de alta calidad. ✨
- Otras: gestión de notas, agenda, documentos, imágenes, etc.

**Reglas de Terminación:**
- Si acabas de recibir un reporte de `deep_research`, **NO** utilices la herramienta de nuevo inmediatamente para el mismo tema. Proporciona la respuesta al usuario basándote en el reporte recibido.
- Tu objetivo es finalizar la investigación y responder, no entrar en un bucle infinito de búsquedas.
"""
        # 5. Generar documentación detallada de las herramientas para modelos que no soportan native tool calling
        tools_documentation = ""
        if tools:
            tools_documentation = "\n\n<b>🛠️ MANUAL DE HERRAMIENTAS DISPONIBLES:</b>\n"
            tools_documentation += "Si tienes problemas para realizar una llamada técnica, usa este formato exacto en tu respuesta para ejecutar una herramienta:\n"
            tools_documentation += "LLAMADA_A_HERRAMIENTA: nombre_herramienta\n"
            tools_documentation += '{"arg1": "valor1", "arg2": "valor2"}\n\n'
            
            for tool in tools:
                try:
                    name = getattr(tool, 'name', str(tool))
                    desc = getattr(tool, 'description', "Sin descripción.")
                    args = ""
                    if hasattr(tool, 'args'):
                        args = str(tool.args)
                    
                    tools_documentation += f"--- HERRAMIENTA: {name} ---\n"
                    tools_documentation += f"Descripción: {desc}\n"
                    if args:
                        tools_documentation += f"Argumentos técnicos esperados: {args}\n"
                    tools_documentation += "\n"
                except:
                    continue
            
        final_prompt_parts = []
        if telegram_id:
            final_prompt_parts.extend([
                TELEGRAM_FORMATTING_PROMPT,
                "<hr>",
            ])
        else:
            final_prompt_parts.extend([
                "💎 **MODO DE DISEÑO PREMIUM ACTIVADO** 💎",
                HTML_DESIGN_PROMPT, # Prioridad absoluta al principio
                "<hr>",
            ])
            
        final_prompt_parts.extend([
            context_instructions,
            user_context_string,
            summary_string,
            "<hr>",
            id_instructions,
            "<hr>",
            tools_capabilities,
            tools_documentation if mode == "prompt_tooling" else "",
            "<hr>",
            "<b>Instrucción crítica:</b> Usa herramientas de una en una. No intentes usar más de una herramienta por respuesta. Espera la siguiente interacción.",
            "<hr>",
            system_prompt_content,
            "<hr>",
            CITATION_SYSTEM_PROMPT,
        ])
        final_prompt_parts.append("\n\nIMPORTANTE: Al citar fuentes, cada número de fuente debe estar entre sus propios corchetes. Por ejemplo, en lugar de [1, 2, 3], formatee como [1][2][3].")
        final_prompt = "\n".join(final_prompt_parts)
        # --- ESCAPE GLOBAL PARA LANGCHAIN ---
        # Garantizamos que NADA en el prompt del sistema sea interpretado como variable por LangChain
        final_prompt = final_prompt.replace('{', '{{').replace('}', '}}')
        
        logger.debug(f"DEBUG (PromptManager): Prompt final del sistema enviado al LLM:\n{final_prompt}")
        return final_prompt


