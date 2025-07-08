# tools/mindmap_generator_tool.py

"""
Herramienta para generar mapas mentales visuales y dinámicos a partir de documentos.
Versión mejorada para KognitoAI: genera datos para renderizado en el frontend.
"""

import asyncio
import logging
import json
import uuid
from typing import Dict, Any, Type
from datetime import datetime

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

# Importaciones del proyecto KognitoAI
from utils.document_analysis import extract_concepts_from_document
from utils.generate_mind_map import (
    generate_visual_mindmap,
    format_mindmap_data,
    generate_mermaid_mindmap,
    generate_mindmap_data_for_frontend
)

logger = logging.getLogger(__name__)

class MindmapGeneratorInput(BaseModel):
    """Esquema de entrada para la herramienta de generación de mapas mentales."""
    document_content: str = Field(..., description="El contenido del documento a analizar.")
    concept_query: str = Field(
        default="temas clave",
        description="La consulta para extraer los conceptos clave (ej. 'temas principales')."
    )
    topic_hint: str = Field(
        default="",
        description="Una pista sobre el tema principal del documento para guiar al LLM."
    )
    account_id: str = Field(
        ...,
        description="El ID de la cuenta del usuario para asociar el mapa mental."
    )
    output_format: str = Field(
        default="mermaid",
        description="Formato de salida: 'mermaid' para código MermaidJS, 'traditional' para imagen PNG, 'both' para ambos."
    )


class MindmapGeneratorTool(BaseTool):
    """
    Herramienta para generar mapas mentales visuales y dinámicos a partir de documentos.
    Soporta múltiples formatos de salida incluyendo MermaidJS y imágenes PNG tradicionales.
    """
    name: str = Field(default="mindmap_generator", description="Nombre de la herramienta")
    description: str = Field(default=(
        "Genera un mapa mental visual y dinámico a partir de un documento. "
        "Esta herramienta analiza el texto, extrae los conceptos principales y sus relaciones, "
        "y devuelve los datos necesarios para que se pueda visualizar un mapa mental interactivo. "
        "Soporta tanto formato MermaidJS para mapas interactivos como imágenes PNG tradicionales."
    ), description="Descripción de la herramienta")
    args_schema: Type[BaseModel] = MindmapGeneratorInput
    account_id: str = Field(default="", description="ID de la cuenta asociada a esta herramienta.")

    def __init__(self, account_id: str = "", **kwargs):
        super().__init__(**kwargs)
        self.account_id = account_id

    async def _arun(self, **kwargs) -> str:
        """
        Ejecuta la herramienta para generar un mapa mental dinámico usando sintaxis Mermaid.
        Devuelve un diccionario estructurado para que el frontend de KognitoAI sepa cómo renderizarlo.
        """
        # Extraer parámetros de kwargs
        document_content = kwargs.get("document_content", "")
        account_id = kwargs.get("account_id", self.account_id)
        concept_query = kwargs.get("concept_query", "temas clave")
        topic_hint = kwargs.get("topic_hint", "")
        output_format = kwargs.get("output_format", "mermaid")

        try:
            # 1. Generar datos del mapa mental según el formato solicitado
            if output_format == "mermaid":
                result_data = await self._generate_mermaid_mindmap(
                    document_content, account_id, concept_query, topic_hint
                )
            elif output_format == "traditional":
                result_data = await self._generate_traditional_mindmap(
                    document_content, account_id, concept_query, topic_hint
                )
            elif output_format == "both":
                result_data = await self._generate_both_formats(
                    document_content, account_id, concept_query, topic_hint
                )
            else:
                # Por defecto usar Mermaid
                result_data = await self._generate_mermaid_mindmap(
                    document_content, account_id, concept_query, topic_hint
                )

            # 2. Guardar el resultado en la base de datos
            task_id = str(uuid.uuid4())
            await self._save_to_database(task_id, account_id, topic_hint, result_data)

            # 3. Devolver respuesta estructurada
            if result_data.get("type") == "error":
                return json.dumps(result_data)

            result_data["task_id"] = task_id
            result_data["message"] = "He generado un mapa mental interactivo para ti. Puedes explorarlo a continuación."

            return json.dumps(result_data)

        except Exception as e:
            logger.exception(f"Error al generar el mapa mental: {e}")
            error_result = {
                "type": "error",
                "content": f"Lo siento, ocurrió un error al generar el mapa mental: {str(e)}"
            }
            return json.dumps(error_result)

    async def _generate_mermaid_mindmap(
        self,
        document_content: str,
        account_id: str,
        concept_query: str,
        topic_hint: str
    ) -> Dict[str, Any]:
        """Genera un mapa mental usando sintaxis MermaidJS."""
        try:
            # Usar la función mejorada de generate_mind_map.py
            return await generate_mindmap_data_for_frontend(
                document_content, topic_hint, concept_query, account_id
            )
        except Exception as e:
            logger.exception(f"Error al generar mapa mental Mermaid: {e}")
            return {
                "type": "error",
                "content": f"Error al generar el mapa mental Mermaid: {str(e)}"
            }

    async def _generate_traditional_mindmap(
        self,
        document_content: str,
        account_id: str,
        concept_query: str,
        topic_hint: str
    ) -> Dict[str, Any]:
        """Genera un mapa mental tradicional usando Graphviz."""
        try:
            # 1. Extraer conceptos
            concepts = await extract_concepts_from_document(document_content, concept_query, topic_hint)
            if not concepts:
                return {"type": "error", "content": "No se pudieron extraer conceptos clave del documento."}

            # 2. Formatear datos y generar imagen
            mindmap_data = format_mindmap_data(concepts)
            main_topics = mindmap_data["main_topics"]
            sub_topics = mindmap_data["sub_topics"]

            base64_image = await generate_visual_mindmap(
                main_topics, sub_topics, topic_hint if topic_hint else "Tema Principal"
            )

            if not base64_image:
                return {"type": "error", "content": "Error al generar el mapa mental visual."}

            return {
                "type": "mindmap_traditional",
                "content": base64_image,
                "title": f"Mapa Mental: {topic_hint or 'Análisis de Documento'}",
                "metadata": {
                    "analysis_type": "mindmap_traditional",
                    "topic": topic_hint or "Tema Principal",
                    "concept_query": concept_query,
                    "created_at": datetime.now().isoformat(),
                    "tool_used": "mindmap_generator_tool.py"
                }
            }

        except Exception as e:
            logger.exception(f"Error al generar mapa mental tradicional: {e}")
            return {
                "type": "error",
                "content": f"Error al generar el mapa mental tradicional: {str(e)}"
            }

    async def _generate_both_formats(
        self,
        document_content: str,
        account_id: str,
        concept_query: str,
        topic_hint: str
    ) -> Dict[str, Any]:
        """Genera ambos formatos: Mermaid y tradicional."""
        try:
            # Generar ambos formatos
            mermaid_result = await self._generate_mermaid_mindmap(
                document_content, account_id, concept_query, topic_hint
            )
            traditional_result = await self._generate_traditional_mindmap(
                document_content, account_id, concept_query, topic_hint
            )

            # Combinar resultados
            return {
                "type": "mindmap_both",
                "content": {
                    "mermaid": mermaid_result.get("content", ""),
                    "traditional": traditional_result.get("content", "")
                },
                "title": f"Mapa Mental Completo: {topic_hint or 'Análisis de Documento'}",
                "metadata": {
                    "analysis_type": "mindmap_both",
                    "topic": topic_hint or "Tema Principal",
                    "concept_query": concept_query,
                    "created_at": datetime.now().isoformat(),
                    "tool_used": "mindmap_generator_tool.py"
                },
                "mermaid_data": mermaid_result,
                "traditional_data": traditional_result
            }

        except Exception as e:
            logger.exception(f"Error al generar ambos formatos: {e}")
            return {
                "type": "error",
                "content": f"Error al generar ambos formatos: {str(e)}"
            }

    async def _save_to_database(
        self,
        task_id: str,
        account_id: str,
        topic_hint: str,
        result_data: Dict[str, Any]
    ) -> None:
        """Guarda el resultado en la base de datos."""
        try:
            from core.database import SessionLocal, MindmapTask

            async with SessionLocal() as db_session:
                account_id_value = uuid.UUID(account_id) if account_id else None

                new_task = MindmapTask(
                    id=uuid.UUID(task_id),
                    account_id=account_id_value,
                    topic=topic_hint if topic_hint else "Tema Principal",
                    status="completed",
                    result_payload=result_data
                )
                db_session.add(new_task)
                await db_session.commit()

        except Exception as e:
            logger.exception(f"Error al guardar en la base de datos: {e}")
            # No lanzamos la excepción para no interrumpir el flujo principal

    def _run(self, **kwargs) -> str:
        """
        Ejecuta la herramienta de generación de mapas mentales de forma síncrona.
        """
        try:
            # Utilizamos asyncio.run para ejecutar la función asíncrona _arun
            result = asyncio.run(self._arun(**kwargs))
            return result
        except Exception as e:
            logger.exception(f"Error al generar el mapa mental: {e}")
            error_result = {
                "type": "error",
                "content": f"Error al generar el mapa mental: {str(e)}"
            }
            return json.dumps(error_result)


# Funciones de utilidad para uso directo

async def generate_mermaid_mindmap_direct(
    document_content: str,
    topic_hint: str = "",
    concept_query: str = "temas clave"
) -> str:
    """
    Función directa para generar código MermaidJS sin usar la herramienta completa.

    Args:
        document_content: El contenido del documento a analizar
        topic_hint: Una pista sobre el tema principal
        concept_query: La consulta para extraer conceptos

    Returns:
        Código MermaidJS para renderizar el mapa mental
    """
    try:
        return await generate_mermaid_mindmap(document_content, topic_hint, concept_query)
    except Exception as e:
        logger.exception(f"Error en generate_mermaid_mindmap_direct: {e}")
        return f"graph TD;\n    A[Error: {str(e)}]"


async def generate_mindmap_for_chat(
    document_content: str,
    account_id: str,
    topic_hint: str = "",
    concept_query: str = "temas clave",
    output_format: str = "mermaid"
) -> Dict[str, Any]:
    """
    Función optimizada para generar mapas mentales desde el chat.

    Args:
        document_content: El contenido del documento a analizar
        account_id: ID de la cuenta del usuario
        topic_hint: Una pista sobre el tema principal
        concept_query: La consulta para extraer conceptos
        output_format: Formato de salida ('mermaid', 'traditional', 'both')

    Returns:
        Diccionario con los datos del mapa mental
    """
    try:
        tool = MindmapGeneratorTool(account_id=account_id)
        result_json = await tool._arun(
            document_content=document_content,
            account_id=account_id,
            concept_query=concept_query,
            topic_hint=topic_hint,
            output_format=output_format
        )

        # Convertir de JSON string a diccionario si es necesario
        if isinstance(result_json, str):
            return json.loads(result_json)
        return result_json

    except Exception as e:
        logger.exception(f"Error en generate_mindmap_for_chat: {e}")
        return {
            "type": "error",
            "content": f"Error al generar el mapa mental: {str(e)}",
            "title": "Error en Generación"
        }
