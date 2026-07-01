# utils/image_generation.py

"""
Módulo para la generación de imágenes utilizando Google AI Studio.

Este módulo proporciona una función asíncrona para generar imágenes a partir de
una descripción textual (prompt) utilizando la API de Google AI Studio (como Imagen 3).
Se encarga de recuperar la API key adecuada (de usuario o del sistema),
construir la petición REST y decodificar el resultado binario.
"""

import logging
import asyncio
import base64
import re
import json
import os
from io import BytesIO
from typing import Union, Optional

# Importaciones del proyecto
from core.config import settings

# Configuración del logger para este módulo.
logger = logging.getLogger(__name__)

# Constante para la clave en user_data donde se guardará la imagen generada.
# Es utilizada por la herramienta de generación y el message_handler.
GENERATED_IMAGE_KEY = "generated_image_bytesio"


async def generar_imagen_vertex_ai_binario(description: str, account_id: Optional[str] = None) -> Union[BytesIO, str]:
    """
    Realiza una petición a la API de Google AI Studio para generar una imagen utilizando Imagen 3.

    Args:
        description: El prompt detallado para la generación de la imagen.
        account_id: El identificador de la cuenta del usuario para buscar credenciales personalizadas.

    Returns:
        Un objeto BytesIO con los datos de la imagen si tiene éxito,
        o una cadena de texto con un mensaje de error si falla.
    """
    try:
        import httpx
        import uuid
        from core.database import SessionLocal
        from core.llm_manager import get_global_llm_settings, get_global_api_key
        from core.repositories.secret_repository import SecretRepository

        # --- 1. Obtener Configuración y Credenciales desde la Base de Datos ---
        model_id = "imagen-3.0-generate-002"
        api_key = None

        async with SessionLocal() as db:
            # Obtener el modelo configurado en los ajustes globales
            try:
                db_settings = await get_global_llm_settings(db)
                model_id = db_settings.get("image_generation_model") or settings.google_image_generation_model_name or "imagen-3.0-generate-002"
            except Exception as e:
                logger.error(f"Error al cargar configuración de modelo de imagen: {e}")
            
            # Limpiar prefijos de proveedor si existen
            if model_id:
                model_id = model_id.replace("gemini/", "").replace("google/", "")
            
            # Intentar obtener la API Key del usuario
            if account_id:
                try:
                    repo = SecretRepository(db)
                    api_key = await repo.get_decrypted_secret(uuid.UUID(account_id), "GOOGLE_API_KEY")
                    if not api_key:
                        api_key = await repo.get_decrypted_secret(uuid.UUID(account_id), "GEMINI_API_KEY")
                    if api_key:
                        logger.debug("Se utilizará la API Key personalizada del usuario.")
                except Exception as e:
                    logger.error(f"Error al obtener API Key personalizada del usuario: {e}")

            # Si no hay API Key del usuario, intentar obtener la API Key global
            if not api_key:
                try:
                    api_key = await get_global_api_key(db, "gemini")
                    if api_key:
                        logger.debug("Se utilizará la API Key global del sistema.")
                except Exception as e:
                    logger.error(f"Error al obtener la API Key global del sistema: {e}")

        # Si aún no hay API Key, usar de variables de entorno o config
        if not api_key:
            api_key = settings.google_api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
            if api_key:
                logger.debug("Se utilizará la API Key configurada en las variables de entorno.")

        if not api_key:
            error_msg = "Configuración incompleta. No se encontró ninguna API Key de Google (Gemini/Google AI Studio) activa."
            logger.error(f"❌ {error_msg}")
            return error_msg

        # --- 2. Construcción del Endpoint ---
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:predict"
        
        headers = {
            "x-goog-api-key": api_key,
            "Content-Type": "application/json; charset=utf-8",
        }

        # --- 3. Detección de Relación de Aspecto en el Prompt ---
        aspect_ratio_param = None
        prompt_lower = description.lower()
        if re.search(r'\b(horizontal|paisaje|panorámica|16:9|16/9)\b', prompt_lower):
            aspect_ratio_param = "16:9"
        elif re.search(r'\b(vertical|retrato|9:16|9/16)\b', prompt_lower):
            aspect_ratio_param = "9:16"
        elif re.search(r'\b(cuadrada|1:1)\b', prompt_lower):
            aspect_ratio_param = "1:1"
        elif re.search(r'\b(3:4|3/4)\b', prompt_lower):
            aspect_ratio_param = "3:4"
        elif re.search(r'\b(4:3|4/3)\b', prompt_lower):
            aspect_ratio_param = "4:3"
        
        if aspect_ratio_param:
            logger.info(f"Relación de aspecto detectada en el prompt: '{aspect_ratio_param}'")

        # --- 4. Construcción del Cuerpo de la Petición (Payload) ---
        data = {
            "instances": [{"prompt": description}],
            "parameters": {"sampleCount": 1}
        }
        if aspect_ratio_param:
            data["parameters"]["aspectRatio"] = aspect_ratio_param

        logger.debug(f"Enviando petición a Google AI Studio. Endpoint: {endpoint}")
        
        # --- 5. Realizar la Petición HTTP ---
        async with httpx.AsyncClient() as client:
            response = await client.post(
                endpoint,
                headers=headers,
                json=data,
                timeout=180.0
            )
            response.raise_for_status()
            resp_json = response.json()
        
        logger.debug("Respuesta recibida exitosamente de Google AI Studio.")

        # --- 6. Procesamiento de la Respuesta ---
        if "predictions" in resp_json and resp_json["predictions"]:
            prediction = resp_json["predictions"][0]
            image_base64 = prediction.get("bytesBase64Encoded") or prediction.get("imageBytes")
            if image_base64:
                image_bytes = base64.b64decode(image_base64)
                
                # Envolver los bytes de la imagen en un objeto BytesIO.
                bio = BytesIO(image_bytes)
                bio.name = 'generated_image.png'
                
                logger.info(f"✅ Imagen generada y decodificada exitosamente usando {model_id} desde Google AI Studio.")
                return bio

        # Si no se encuentra la imagen en la respuesta esperada.
        error_detail = resp_json.get("error", {}).get("message", "La respuesta no contenía una imagen válida.")
        logger.error(f"❌ Respuesta inesperada de Google AI Studio: {error_detail}")
        return f"Error: No se recibió la imagen en la respuesta de la API. Detalle: {error_detail}"

    except httpx.HTTPStatusError as e:
        response_text = e.response.text if e.response else "Sin respuesta del servidor."
        logger.error(f"❌ Error HTTP a Google AI Studio: {e}. Respuesta: {response_text}", exc_info=True)
        try:
            error_detail = e.response.json().get("error", {}).get("message", response_text)
            return f"Error al generar imagen: Fallo en la API. Detalle: {error_detail}"
        except json.JSONDecodeError:
            return f"Error al generar imagen: Fallo en la API con status {e.response.status_code}. Respuesta no es JSON."
    except Exception as e:
        logger.error(f"❌ Error inesperado al generar imagen con Google AI Studio: {e}", exc_info=True)
        return f"Error inesperado al procesar la solicitud de imagen: {e}"
