# core/actions.py
import logging
from typing import Dict, Any
from core.database import SessionLocal  #  Asegúrate de que esto esté correctamente configurado
from core.llm_manager import get_llm  #  Asegúrate de que esto esté correctamente configurado
from knowledge_graph.graph_database import GraphDB  #  Importa la clase GraphDB
from knowledge_graph.cognee_integration import CogneeIntegration  #  Importa CogneeIntegration
from core.config import settings  #  Importa las configuraciones
from telegram.constants import PARSE_MODE_HTML  #  Si usas Telegram
import asyncio

logger = logging.getLogger(__name__)

async def crear_concepto_en_grafo(data: Dict[str, Any], telegram_id: int = None) -> str:
    """
    Crea un nuevo concepto en la base de datos de grafos utilizando la información proporcionada.

    Args:
        data (Dict[str, Any]): Un diccionario con la información del concepto (nombre, descripción, etc.).
        telegram_id (int, optional): El ID de Telegram del usuario que realiza la acción. Defaults to None.

    Returns:
        str: Un mensaje indicando el resultado de la operación.
    """
    try:
        #  Obtener la instancia de GraphDB desde el estado de la aplicación
        graph_db: GraphDB = app.state.graph_db

        #  Crear el nodo en la base de datos de grafos
        concepto = graph_db.create_node("Concepto", data)

        #  Construir un mensaje de éxito
        mensaje = f"Concepto '{data['nombre']}' creado exitosamente en la base de datos de grafos."

        #  Enviar un mensaje de confirmación al usuario (si se proporciona un ID de Telegram)
        if telegram_id:
            bot = app.state.bot
            await bot.send_message(chat_id=telegram_id, text=mensaje, parse_mode=PARSE_MODE_HTML)

        return mensaje

    except Exception as e:
        #  Registrar el error
        logger.error(f"Error al crear el concepto en el grafo: {e}", exc_info=True)

        #  Construir un mensaje de error
        mensaje = f"Error al crear el concepto en el grafo: {e}"

        #  Enviar un mensaje de error al usuario (si se proporciona un ID de Telegram)
        if telegram_id:
            bot = app.state.bot
            await bot.send_message(chat_id=telegram_id, text=mensaje, parse_mode=PARSE_MODE_HTML)

        return mensaje

async def ejecutar_plan_cognee(objetivo: str, telegram_id: int = None) -> str:
    """
    Ejecuta un plan utilizando Cognee para alcanzar un objetivo específico.

    Args:
        objetivo (str): El objetivo que se desea alcanzar.
        telegram_id (int, optional): El ID de Telegram del usuario que realiza la acción. Defaults to None.

    Returns:
        str: Un mensaje indicando el resultado de la operación.
    """
    try:
        #  Obtener las instancias de GraphDB y CogneeIntegration desde el estado de la aplicación
        graph_db: GraphDB = app.state.graph_db
        cognee_integration: CogneeIntegration = app.state.cognee_integration

        #  Convertir el grafo a PDDL
        pddl_data = cognee_integration.convert_graph_to_pddl()

        #  Ejecutar el plan en Cognee
        plan_result = cognee_integration.execute_plan(pddl_data['domain'], pddl_data['problem'])

        #  Integrar los resultados de Cognee en la base de datos de grafos
        cognee_integration.integrate_cognee_results(plan_result)

        #  Construir un mensaje de éxito
        mensaje = f"Plan ejecutado exitosamente utilizando Cognee. Resultados: {plan_result}"

        #  Enviar un mensaje de confirmación al usuario (si se proporciona un ID de Telegram)
        if telegram_id:
            bot = app.state.bot
            await bot.send_message(chat_id=telegram_id, text=mensaje, parse_mode=PARSE_MODE_HTML)

        return mensaje

    except Exception as e:
        #  Registrar el error
        logger.error(f"Error al ejecutar el plan en Cognee: {e}", exc_info=True)

        #  Construir un mensaje de error
        mensaje = f"Error al ejecutar el plan en Cognee: {e}"

        #  Enviar un mensaje de error al usuario (si se proporciona un ID de Telegram)
        if telegram_id:
            bot = app.state.bot
            await bot.send_message(chat_id=telegram_id, text=mensaje, parse_mode=PARSE_MODE_HTML)

        return mensaje

async def consultar_grafo(query: str, telegram_id: int = None) -> str:
    """
    Ejecuta una consulta en la base de datos de grafos y devuelve los resultados.

    Args:
        query (str): La consulta Cypher a ejecutar.
        telegram_id (int, optional): El ID de Telegram del usuario que realiza la acción. Defaults to None.

    Returns:
        str: Un mensaje con los resultados de la consulta.
    """
    try:
        #  Obtener la instancia de GraphDB desde el estado de la aplicación
        graph_db: GraphDB = app.state.graph_db

        #  Ejecutar la consulta en la base de datos de grafos
        resultados = graph_db.execute_query(query)

        #  Construir un mensaje con los resultados
        mensaje = f"Resultados de la consulta: {resultados}"

        #  Enviar un mensaje con los resultados al usuario (si se proporciona un ID de Telegram)
        if telegram_id:
            bot = app.state.bot
            await bot.send_message(chat_id=telegram_id, text=mensaje, parse_mode=PARSE_MODE_HTML)

        return mensaje

    except Exception as e:
        #  Registrar el error
        logger.error(f"Error al ejecutar la consulta en el grafo: {e}", exc_info=True)

        #  Construir un mensaje de error
        mensaje = f"Error al ejecutar la consulta en el grafo: {e}"

        #  Enviar un mensaje de error al usuario (si se proporciona un ID de Telegram)
        if telegram_id:
            bot = app.state.bot
            await bot.send_message(chat_id=telegram_id, text=mensaje, parse_mode=PARSE_MODE_HTML)

        return mensaje

#  Ejemplo de uso (puedes agregar esto a tu sistema de comandos o API)
async def handle_action(action_name: str, data: Dict[str, Any], telegram_id: int = None) -> str:
    """
    Maneja una acción específica basada en el nombre de la acción y los datos proporcionados.

    Args:
        action_name (str): El nombre de la acción a realizar.
        data (Dict[str, Any]): Un diccionario con los datos necesarios para realizar la acción.
        telegram_id (int, optional): El ID de Telegram del usuario que realiza la acción. Defaults to None.

    Returns:
        str: Un mensaje indicando el resultado de la operación.
    """
    try:
        if action_name == "crear_concepto":
            return await crear_concepto_en_grafo(data, telegram_id)
        elif action_name == "ejecutar_plan":
            return await ejecutar_plan_cognee(data['objetivo'], telegram_id)
        elif action_name == "consultar_grafo":
            return await consultar_grafo(data['query'], telegram_id)
        else:
            return f"Acción desconocida: {action_name}"

    except Exception as e:
        #  Registrar el error
        logger.error(f"Error al manejar la acción: {e}", exc_info=True)

        #  Construir un mensaje de error
        mensaje = f"Error al manejar la acción: {e}"

        #  Enviar un mensaje de error al usuario (si se proporciona un ID de Telegram)
        if telegram_id:
            bot = app.state.bot
            await bot.send_message(chat_id=telegram_id, text=mensaje, parse_mode=PARSE_MODE_HTML)

        return mensaje