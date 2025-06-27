from typing import Any, Dict, List, Optional
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
import asyncio
import json
import uuid
import logging

# Importar el LLM manager
from core.llm_manager import get_fast_llm
# Importar la herramienta para obtener contenido de documentos
from tools.get_document_content_tool import GetDocumentContentTool
# Importar la nueva utilidad para análisis de documentos
from utils.document_analysis import extract_concepts_from_document
# Importar la nueva utilidad para generar el mapa visual
from utils.generate_map_mind import generate_visual_mindmap # Asegúrate de que esta utilidad exista y sea accesible

# Importar para tareas en segundo plano y base de datos
from fastapi import BackgroundTasks # Esto se usará en el endpoint que invoca la herramienta, no directamente en la clase Tool
from core.database import SessionLocal, MindmapTask
from sqlalchemy import update

logger = logging.getLogger(__name__)

# 1. Definición del Esquema de Entrada (Input Schema)
class MindmapInput(BaseModel):
    account_id: str = Field(description="El identificador universal (UUID) de la cuenta del usuario.")
    topic: str = Field(description="El tema central para el mapa mental. Puede ser inferido del documento si se proporciona.")
    ideas_input: str = Field(
        "", description="Ideas o palabras clave adicionales para incluir en el mapa mental, separadas por comas o saltos de línea."
    )
    document_name: str = Field(
        "", description="El nombre del documento del cual extraer conceptos clave para el mapa mental."
    )
    concept_query: str = Field(
        "conceptos clave", description="Tipo de información a extraer del documento, por ejemplo: 'conceptos clave', 'puntos importantes', 'resumen'."
    )

# 2. Clase de la Herramienta (Tool Class)
class MindmapTool(BaseTool):
    name: str = "mindmap_tool"
    description = "Util para generar un mapa mental en formato de texto a partir de un tema, un conjunto de ideas, o extrayendo conceptos clave de un documento. Puede expandir ideas usando inteligencia artificial."
    args_schema: type[BaseModel] = MindmapInput
    
    # MODIFICACIÓN CLAVE AQUÍ: Aceptar account_id y otros kwargs
    def __init__(self, account_id: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.account_id = account_id # Almacenar account_id si es necesario para la instancia de la herramienta

    # Implementación SÍNCRONA requerida por BaseTool
    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """Síncrono run no implementado, usar _arun."""
        raise NotImplementedError("MindmapTool solo soporta ejecución asíncrona (_arun).")

    async def _arun(self, account_id: str, topic: str, ideas_input: str = "", document_name: str = "", concept_query: str = "conceptos clave") -> str:
        """
        Inicia la generación del mapa mental en segundo plano y devuelve un ID de tarea.
        """
        logger.info(f"MindmapTool._arun llamado para account_id: {account_id}, topic: {topic}")
        
        # Crear una nueva tarea en la base de datos
        async with SessionLocal() as db_session:
            new_task = MindmapTask(
                account_id=uuid.UUID(account_id),
                topic=topic,
                ideas_input=ideas_input,
                document_name=document_name,
                concept_query=concept_query,
                status="pending"
            )
            db_session.add(new_task)
            await db_session.commit()
            await db_session.refresh(new_task)
            task_id = str(new_task.id)
        
        logger.info(f"Tarea de mapa mental creada con ID: {task_id}. Programando en segundo plano.")
        
        # IMPORTANTE: BackgroundTasks se maneja en el endpoint de FastAPI, no directamente aquí.
        # Aquí, simplemente programamos la corrutina para que se ejecute en el bucle de eventos.
        # El framework de FastAPI (o similar) es el que se encarga de pasarla a BackgroundTasks.
        asyncio.create_task(self._run_mindmap_background(task_id, account_id, topic, ideas_input, document_name, concept_query))
        
        return f"Tarea de generación de mapa mental iniciada. ID de tarea: {task_id}. Recibirás una notificación cuando esté listo."

    async def _generate_expanded_ideas(self, topic: str, ideas_input: str) -> Dict[str, List[str]]:
        """
        Genera ideas expandidas utilizando un LLM real, estructuradas para el mapa mental.
        """
        llm = get_fast_llm()
        if llm is None:
            logger.warning("LLM no disponible para _generate_expanded_ideas. Usando ideas por defecto.")
            return {
                "Tema Central - Concepto 1": ["Subconcepto 1.1", "Subconcepto 1.2"],
                "Tema Central - Concepto 2": ["Subconcepto 2.1", "Subconcepto 2.2"],
                "Tema Central - Concepto 3": ["Subconcepto 3.1", "Subconcepto 3.2"]
            }

        ideas_text = ""
        if ideas_input:
            ideas_text = "Ideas adicionales proporcionadas para incorporar: " + ideas_input
        
        prompt = f"""Genera una estructura de mapa mental detallada sobre el tema '{topic}'.
Incluye al menos 3-5 ideas principales y 2-3 sub-ideas para cada una.
Si se proporcionan ideas adicionales, incorpóralas y expándelas de forma coherente.
{ideas_text}

Formato de salida requerido (JSON):
```json
{{
  "Idea Principal 1": [
    "Sub-idea 1.1",
    "Sub-idea 1.2"
  ],
  "Idea Principal 2": [
    "Sub-idea 2.1",
    "Sub-idea 2.2"
  ]
}}
```"""

        try:
            llm_response = await llm.ainvoke(prompt)
            response_content = llm_response.content.strip()
            
            # Limpiar la respuesta si contiene etiquetas de código markdown
            if response_content.startswith("```json"):
                response_content = response_content[7:-3].strip()
            elif response_content.startswith("```"): # Para el caso de ```python, ```text, etc.
                response_content = response_content.split("\n", 1)[1].rsplit("\n", 1)[0].strip()

            return json.loads(response_content)
        except json.JSONDecodeError as e:
            logger.error(f"Error al parsear JSON de la respuesta del LLM: {e}. Respuesta: {response_content}", exc_info=True)
            return {
                "Error al generar ideas": ["Formato JSON inválido", str(e)]
            }
        except Exception as error:
            logger.error(f"Error al generar ideas expandidas con LLM: {error}", exc_info=True)
            return {
                "Tema Central - Concepto 1": ["Subconcepto 1.1", "Subconcepto 1.2"],
                "Tema Central - Concepto 2": ["Subconcepto 2.1", "Subconcepto 2.2"],
                "Tema Central - Concepto 3": ["Subconcepto 3.1", "Subconcepto 3.2"]
            }

    async def _run_mindmap_background(self, task_id: str, account_id: str, topic: str, ideas_input: str, document_name: str, concept_query: str):
        """
        Ejecuta la generación del mapa mental (incluyendo la visualización) en segundo plano
        y actualiza el estado de la tarea en la base de datos.
        """
        async with SessionLocal() as db_session:
            try:
                # Marcar la tarea como 'processing'
                stmt_processing = update(MindmapTask).where(MindmapTask.id == uuid.UUID(task_id)).values(status="processing")
                await db_session.execute(stmt_processing)
                await db_session.commit()
                
                logger.info(f"Iniciando generación de mapa mental para tarea {task_id} en segundo plano...")
                final_ideas_to_process = ideas_input if ideas_input else ""
                generated_from_doc = False

                if document_name:
                    logger.info(f"Intentando obtener contenido del documento: {document_name}")
                    try:
                        document_tool = GetDocumentContentTool()
                        document_content_response = await document_tool._arun(account_id=account_id, file_name=document_name)
                        document_content = document_content_response

                        if document_content and not document_content.startswith("Error") and not document_content.startswith("No pude encontrar") and not document_content.startswith("Ocurrió un error"):
                            logger.info(f"Contenido del documento '{document_name}' obtenido. Extrayendo {concept_query}...")
                            extracted_concepts = await extract_concepts_from_document(document_content, concept_query, topic)
                            if extracted_concepts:
                                final_ideas_to_process = f"{final_ideas_to_process}\n{extracted_concepts}" if final_ideas_to_process else extracted_concepts
                                generated_from_doc = True
                                logger.info(f"Conceptos extraídos del documento: {extracted_concepts[:100]}...")
                            else:
                                logger.warning("No se pudieron extraer conceptos del documento.")
                        else:
                            error_msg = f"Error: No se pudo obtener el contenido del documento '{document_name}'. Por favor, verifica el nombre del archivo."
                            logger.error(error_msg)
                            stmt_failed = update(MindmapTask).where(MindmapTask.id == uuid.UUID(task_id)).values(
                                status="failed", result_payload={"error": error_msg})
                            await db_session.execute(stmt_failed)
                            await db_session.commit()
                            return
                    except Exception as e:
                        error_msg = f"Error al acceder o procesar el documento '{document_name}': {e}"
                        logger.error(error_msg, exc_info=True)
                        stmt_failed = update(MindmapTask).where(MindmapTask.id == uuid.UUID(task_id)).values(
                            status="failed", result_payload={"error": error_msg})
                        await db_session.execute(stmt_failed)
                        await db_session.commit()
                        return

                if not final_ideas_to_process and not generated_from_doc:
                    logger.info("No hay ideas iniciales ni del documento. Generando ideas básicas basadas en el tema.")
                    llm_generated_ideas = await self._generate_expanded_ideas(topic, "")
                else:
                    logger.info("Generando ideas expandidas con LLM a partir de las ideas recopiladas.")
                    llm_generated_ideas = await self._generate_expanded_ideas(topic, final_ideas_to_process)

                # Generar el mapa mental visual (Base64)
                visual_map_base64 = ""
                if llm_generated_ideas:
                    visual_map_base64 = await generate_visual_mindmap(llm_generated_ideas, topic)
                    if not visual_map_base64:
                        logger.warning("No se pudo generar el mapa mental visual. Se guardará solo la estructura de texto.")
                else:
                    logger.warning("No se generaron ideas para el mapa mental. No se creará visualización.")

                # Generar la representación en texto (siempre útil como fallback o complemento)
                mindmap_text_output = f"# Mapa Mental: {topic}\n\n"
                if llm_generated_ideas:
                    mindmap_text_output += "## Ideas Principales (Generadas/Expandidas por IA)\n"
                    for main_idea, sub_ideas in llm_generated_ideas.items():
                        mindmap_text_output += f"- **{main_idea}**\n"
                        for sub_idea in sub_ideas:
                            mindmap_text_output += f"  - {sub_idea}\n"
                else:
                    mindmap_text_output += "No se pudieron generar ideas complejas con el LLM. Generando estructura básica.\n"
                    mindmap_text_output += "## Subtema 1\n- Idea A\n  - Detalle A1\n- Idea B\n\n"
                    mindmap_text_output += "## Subtema 2\n- Idea C\n  - Detalle C1\n"
                mindmap_text_output += "\n*Este es un prototipo de mapa mental en texto, con ideas expandidas por IA. Puedes copiarlo y usarlo como base para herramientas de visualización o para organizar tus pensamientos.*"

                # Guardar el resultado y marcar como 'completed'
                result_payload = {
                    "text_mindmap": mindmap_text_output,
                    "visual_mindmap_base64": visual_map_base64 if visual_map_base64 else None,
                    "status_message": "Mapa mental generado exitosamente."
                }
                stmt_completed = update(MindmapTask).where(MindmapTask.id == uuid.UUID(task_id)).values(
                    status="completed", result_payload=result_payload)
                await db_session.execute(stmt_completed)
                await db_session.commit()
                logger.info(f"Mapa mental para tarea {task_id} completado y resultado guardado en DB.")
                
                # NOTIFICACIÓN AL USUARIO FINAL
                # Se necesita un mecanismo para notificar al usuario que la tarea ha terminado
                # y enviarle el resultado (la imagen Base64). Esto puede ser a través de un endpoint API
                # que el frontend consulte para obtener los resultados de tareas completadas,
                # o mediante un sistema de notificaciones WebSocket.
                logger.info(f"Tarea de mapa mental {task_id} completada. Se requiere notificar al frontend con el resultado (imagen Base64). Considera implementar un endpoint en run_api.py para obtener resultados de MindmapTask con estado 'completed'.")

            except Exception as e:
                logger.error(f"Fallo crítico en tarea de mapa mental {task_id}: {e}", exc_info=True)
                error_msg = f"Ocurrió un error inesperado al generar el mapa mental: {str(e)}"
                stmt_failed = update(MindmapTask).where(MindmapTask.id == uuid.UUID(task_id)).values(
                    status="failed", result_payload={"error": error_msg})
                await db_session.execute(stmt_failed)
                await db_session.commit()
                logger.info(f"Tarea de mapa mental {task_id} marcada como fallida en DB.")
