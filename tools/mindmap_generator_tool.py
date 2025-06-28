# tools/mindmap_generator_tool.py

"""Herramienta para generar mapas mentales visuales a partir de documentos."""

import asyncio
import logging
from typing import Dict, Any

from langchain_core.tools import Tool

# Importa la función extract_concepts_from_document desde utils/document_analysis.py
from utils.document_analysis import extract_concepts_from_document
# Importa la función generate_visual_mindmap desde utils/generate_mind_map.py
from utils.generate_mind_map import generate_visual_mindmap
# Importa la función format_mindmap_data desde utils/mindmap_utils.py
from utils.generate_mind_map import format_mindmap_data

logger = logging.getLogger(__name__)

from pydantic import BaseModel, Field
from typing import Type
from langchain_core.tools import BaseTool

class MindmapGeneratorInput(BaseModel):
    document_content: str = Field(..., description="El contenido del documento a analizar.")
    concept_query: str = Field(default="temas clave", description="La consulta para extraer los conceptos clave (ej. 'temas principales', 'conceptos clave').")
    topic_hint: str = Field(default="", description="Una pista sobre el tema principal del documento.")
    account_id: str = Field(..., description="El ID de la cuenta del usuario para asociar el mapa mental.") # <--- AÑADIR ESTA LÍNEA
class MindmapGeneratorTool(BaseTool):
    name = "mindmap_generator"
    description = """
    Genera un mapa mental visual a partir de un documento.

    Args:
        document_content (str): El contenido del documento a analizar.
        concept_query (str): La consulta para extraer los conceptos clave (ej. "temas principales", "conceptos clave").
        topic_hint (str): Una pista sobre el tema principal del documento.

    Returns:
        Una cadena Base64 de la imagen PNG generada, o una cadena vacía si hay un error.
    """
    args_schema: Type[BaseModel] = MindmapGeneratorInput
    account_id: str = Field(default="", description="ID de la cuenta asociada a esta herramienta.")

    def __init__(self, account_id: str = "", **kwargs):
        super().__init__(**kwargs)
        self.account_id = account_id

    async def _arun(self, document_content: str, account_id: str, concept_query: str = "temas clave", topic_hint: str = "") -> str:
        """
        Ejecuta la herramienta de generación de mapas mentales de forma asíncrona.
        """
        from core.database import SessionLocal, MindmapTask
        from sqlalchemy import update
        import uuid

        try:
            # 1. Extraer temas clave del documento utilizando la función existente
            concepts = await extract_concepts_from_document(document_content, concept_query, topic_hint)
            if not concepts:
                return "No se pudieron extraer conceptos clave del documento."

            # 2. Formatear los datos para que sean compatibles con generate_visual_mindmap
            mindmap_data = format_mindmap_data(concepts)
            main_topics = mindmap_data["main_topics"]
            sub_topics = mindmap_data["sub_topics"]

            # 3. Generar el mapa mental visual
            base64_image = await generate_visual_mindmap(main_topics, sub_topics, topic_hint if topic_hint else "Tema Principal")

            if not base64_image:
                return "Error al generar el mapa mental visual."

            # 4. Guardar el resultado en la base de datos
            task_id = str(uuid.uuid4())
            async with SessionLocal() as db_session:
                # Si no hay account_id, usamos None y dejamos que la base de datos maneje el valor por defecto si está configurado
                account_id_value = uuid.UUID(self.account_id) if self.account_id else None
                new_task = MindmapTask(
                    id=uuid.UUID(task_id),
                    account_id=account_id_value,
                    topic=topic_hint if topic_hint else "Tema Principal",
                    status="completed",
                    result_payload={"base64_image": base64_image}
                )
                db_session.add(new_task)
                try:
                    await db_session.commit()
                except Exception as db_error:
                    logger.error(f"Error al guardar en la base de datos: {db_error}")
                    # Si falla el guardado debido a restricciones NOT NULL, intentamos sin account_id
                    if "not-null constraint" in str(db_error).lower() and account_id_value is None:
                        logger.warning("Reintentando sin account_id debido a restricción NOT NULL.")
                        new_task.account_id = None
                        db_session.add(new_task)
                        await db_session.commit()

            # 5. Devolver un mensaje con el ID de tarea para referencia
            return f"Mapa mental generado con éxito. ID de tarea: {task_id}"

        except Exception as e:
            logger.exception(f"Error al generar el mapa mental: {e}")
            return f"Error al generar el mapa mental: {str(e)}"

    def _run(self, document_content: str, concept_query: str = "temas clave", topic_hint: str = "") -> str:
        """
        Ejecuta la herramienta de generación de mapas mentales de forma síncrona (adaptada para ser llamada desde un contexto asíncrono).
        """
        try:
            # Utilizamos asyncio.run para ejecutar la función asíncrona _arun
            result = asyncio.run(
                self._arun(document_content, concept_query, topic_hint)
            )
            return result
        except Exception as e:
            logger.exception(f"Error al generar el mapa mental: {e}")
            return f"Error al generar el mapa mental: {e}"
