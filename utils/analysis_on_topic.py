# utils/analysis_on_topic.py

"""
Utilidad para realizar análisis profundo en la base de conocimientos del usuario.

Esta utilidad proporciona funciones para analizar la base de conocimientos del usuario en función de un tema específico,
identificando conexiones, patrones y conocimientos relevantes. Es utilizada por herramientas de análisis profundo para
explorar temas específicos dentro de la base de conocimientos.
"""

import logging
from typing import Any, Dict, Optional, List
import uuid
import asyncio
from datetime import datetime
from sqlalchemy import text
from core.database import SessionLocal, engine
from core.llm_manager import get_fast_llm
from core.memory_manager import list_user_documents, get_full_document_content
from utils.db_session import DBSession
import json

logger = logging.getLogger(__name__)

async def deep_analysis_on_topic(
    account_id: str,
    topic: str,
    thread_id: str,
    parameters: Optional[Dict[str, Any]] = None
) -> str:
    """
    Inicia un análisis profundo sobre un tema específico en la base de conocimientos del usuario.
    La tarea se ejecuta en segundo plano y el usuario recibe una notificación cuando se completa.
    
    Args:
        account_id (str): Identificador único de la cuenta del usuario.
        topic (str): Tema sobre el cual realizar el análisis.
        thread_id (str): Identificador del hilo de chat donde se mostrará el resultado.
        parameters (dict, optional): Parámetros adicionales para personalizar el análisis.
        
    Returns:
        str: Mensaje indicando que la tarea ha comenzado y que se notificará al usuario cuando se complete.
    """
    logger.info(f"Iniciando análisis profundo para el usuario {account_id} sobre el tema '{topic}' en el hilo {thread_id}")
    
    # Establecer valores predeterminados para los parámetros si no se proporcionan
    if parameters is None:
        parameters = {}
    
    depth = parameters.get("depth", "moderate")
    scope = parameters.get("scope", "all")
    time_frame = parameters.get("time_frame", "")
    
    logger.info(f"Parámetros de análisis: depth={depth}, scope={scope}, time_frame={time_frame}")
    
    # Crear una tarea en segundo plano para el análisis
    task_id = str(uuid.uuid4())
    async with DBSession(SessionLocal) as db:
        try:
            # Registrar la tarea en la base de datos
            insert_query = text("""
                INSERT INTO analysis_tasks (id, account_id, file_name, status, analysis_type, created_at, updated_at)
                VALUES (:task_id, :account_id, :topic, 'pending', 'topic_analysis', NOW(), NOW())
            """)
            await db.execute(insert_query, {"task_id": task_id, "account_id": account_id, "topic": topic})
            await db.commit()
            
            # Iniciar la tarea en segundo plano
            asyncio.create_task(perform_background_analysis(
                task_id, account_id, topic, thread_id, depth, scope, time_frame
            ))
            
            logger.info(f"Tarea de análisis profundo iniciada con ID {task_id} para el tema '{topic}'")
            return f"El análisis profundo sobre '{topic}' ha comenzado. Recibirás una notificación en este chat cuando se complete. ID de tarea: {task_id}."
        except Exception as e:
            logger.error(f"Error al iniciar la tarea de análisis profundo para el usuario {account_id}: {e}", exc_info=True)
            await db.rollback()
            return f"Error al iniciar el análisis profundo sobre '{topic}'. Por favor, intenta de nuevo."

async def perform_background_analysis(
    task_id: str,
    account_id: str,
    topic: str,
    thread_id: str,
    depth: str,
    scope: str,
    time_frame: str
) -> None:
    """
    Realiza el análisis profundo en segundo plano y actualiza el estado de la tarea.
    
    Args:
        task_id (str): Identificador único de la tarea.
        account_id (str): Identificador único de la cuenta del usuario.
        topic (str): Tema sobre el cual realizar el análisis.
        thread_id (str): Identificador del hilo de chat donde se mostrará el resultado.
        depth (str): Profundidad del análisis ('shallow', 'moderate', 'deep').
        scope (str): Alcance del análisis ('all', 'personal', 'team').
        time_frame (str): Marco temporal para filtrar documentos.
    """
    logger.info(f"Ejecutando análisis profundo en segundo plano con ID {task_id} para el tema '{topic}'")
    
    async with DBSession(SessionLocal) as db:
        try:
            # Actualizar estado a 'processing'
            update_query = text("""
                UPDATE analysis_tasks
                SET status = 'processing', updated_at = NOW()
                WHERE id = :task_id
            """)
            await db.execute(update_query, {"task_id": task_id})
            await db.commit()
            
            # Obtener documentos relevantes
            documents = await list_user_documents(account_id)
            relevant_docs = []
            for doc in documents:
                if topic.lower() in doc.get('topic', '').lower() or topic.lower() in doc.get('file_name', '').lower():
                    content = await get_full_document_content(account_id, doc['file_name'])
                    if content:
                        relevant_docs.append({
                            'file_name': doc['file_name'],
                            'content': content,
                            'metadata': doc
                        })
            
            if not relevant_docs:
                logger.warning(f"No se encontraron documentos relevantes para el tema '{topic}'")
                result_payload = json.dumps({"error": f"No se encontraron documentos relevantes para el tema '{topic}' en tu base de conocimientos."})
                status = "failed"
            else:
                logger.info(f"Se encontraron {len(relevant_docs)} documentos relevantes para el tema '{topic}'")
                # Realizar análisis con LLM
                analysis_result = await perform_llm_analysis(relevant_docs, topic, depth)
                result_payload = json.dumps({"result": analysis_result})
                status = "completed"
            
            # Actualizar estado y resultado de la tarea
            update_result_query = text("""
                UPDATE analysis_tasks
                SET status = :status, result_payload = CAST(:result_payload AS jsonb), updated_at = NOW()
                WHERE id = :task_id
            """)
            await db.execute(update_result_query, {
                "task_id": task_id,
                "status": status,
                "result_payload": result_payload
            })
            await db.commit()
            
            # Enviar notificación al hilo de chat
            await send_notification_to_chat(thread_id, account_id, topic, task_id, status, result_payload)
            
            logger.info(f"Análisis profundo completado con ID {task_id} para el tema '{topic}' con estado '{status}'")
        except Exception as e:
            logger.error(f"Error durante el análisis profundo en segundo plano con ID {task_id}: {e}", exc_info=True)
            await db.rollback()
            # Actualizar estado a 'failed' en caso de error
            update_error_query = text("""
                UPDATE analysis_tasks
                SET status = 'failed', error_message = :error_message, updated_at = NOW()
                WHERE id = :task_id
            """)
            await db.execute(update_error_query, {
                "task_id": task_id,
                "error_message": str(e)
            })
            await db.commit()
            # Enviar notificación de error al hilo de chat
            await send_notification_to_chat(thread_id, account_id, topic, task_id, "failed", json.dumps({"error": str(e)}))

async def perform_llm_analysis(documents: List[Dict[str, Any]], topic: str, depth: str) -> str:
    """
    Realiza un análisis profundo utilizando un LLM sobre los documentos proporcionados.
    
    Args:
        documents (list): Lista de documentos relevantes para el análisis.
        topic (str): Tema del análisis.
        depth (str): Profundidad del análisis ('shallow', 'moderate', 'deep').
        
    Returns:
        str: Resultado del análisis profundo.
    """
    logger.info(f"Realizando análisis con LLM sobre {len(documents)} documentos para el tema '{topic}' con profundidad '{depth}'")
    
    llm = get_fast_llm()
    if llm is None:
        logger.error("No se pudo obtener la instancia del LLM rápido.")
        return "Error: No se pudo obtener la instancia del LLM para el análisis."
    
    # Determinar el número de documentos a analizar basado en la profundidad
    if depth == "shallow":
        doc_limit = min(3, len(documents))
    elif depth == "moderate":
        doc_limit = min(6, len(documents))
    else:  # deep
        doc_limit = len(documents)
    
    # Limitar los documentos a analizar según la profundidad
    selected_docs = documents[:doc_limit]
    logger.info(f"Seleccionados {len(selected_docs)} documentos para análisis con LLM con profundidad '{depth}'")
    
    # Preparar el contenido para el análisis
    doc_summaries = []
    for i, doc in enumerate(selected_docs):
        content = doc['content'][:2000]  # Limitar a 2000 caracteres por documento
        doc_summaries.append(f"Documento {i+1} ({doc['file_name']}): {content}")
    
    content_text = "\n\n".join(doc_summaries)
    prompt = f"""Realiza un análisis profundo sobre el tema '{topic}' basado en los siguientes documentos extraídos de mi base de conocimientos.
    La profundidad del análisis debe ser '{depth}', lo que significa que debes identificar conceptos clave, conexiones y patrones según el nivel de detalle solicitado.
    Devuelve un informe detallado con secciones claras para conceptos clave, conexiones y patrones (si aplica).

    Documentos:
    {content_text}

    Informe de análisis sobre '{topic}':
    """
    
    try:
        llm_response = await llm.ainvoke(prompt)
        analysis_result = llm_response.content.strip()
        logger.info(f"Análisis con LLM completado para el tema '{topic}'")
        return analysis_result
    except Exception as e:
        logger.error(f"Error al realizar análisis con LLM para el tema '{topic}': {e}", exc_info=True)
        return f"Error al realizar el análisis con LLM: {str(e)}"

async def send_notification_to_chat(thread_id: str, account_id: str, topic: str, task_id: str, status: str, result_payload: str) -> None:
    """
    Simula el envío de una notificación al hilo de chat con el resultado del análisis.
    En una implementación real, esto interactuaría con el frontend para mostrar una tarjeta de notificación.
    
    Args:
        thread_id (str): Identificador del hilo de chat.
        account_id (str): Identificador único de la cuenta del usuario.
        topic (str): Tema del análisis.
        task_id (str): Identificador único de la tarea.
        status (str): Estado de la tarea ('completed' o 'failed').
        result_payload (str): Resultado o error del análisis en formato JSON.
    """
    logger.info(f"Enviando notificación al hilo {thread_id} para la tarea {task_id} con estado '{status}'")
    
    # Aquí se simula el envío de un mensaje al chat
    # En una implementación real, esto interactuaría con la API del chat para enviar un mensaje
    result_dict = json.loads(result_payload)
    message_content = f"Análisis profundo sobre '{topic}' (ID de tarea: {task_id}) ha finalizado con estado: {status}.\n\n"
    if status == "completed":
        message_content += "Resultado:\n" + result_dict.get("result", "No hay resultado disponible.")
    else:
        message_content += "Error:\n" + result_dict.get("error", "Error desconocido.")
    
    logger.info(f"Notificación simulada enviada al hilo {thread_id}: {message_content[:100]}...")
    # TODO: Implementar la lógica real para enviar el mensaje al chat usando la API correspondiente
    # Esto debería integrarse con el sistema de notificaciones del frontend en 'src/components/ui/toaster.tsx'
    # utilizando el hook 'useToast' para mostrar notificaciones emergentes en la esquina superior derecha.
    # Es posible que las notificaciones toast sean manejadas por un endpoint específico en el frontend.
