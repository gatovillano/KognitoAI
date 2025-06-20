# utils/image_generation.py

"""
Módulo para la generación de imágenes utilizando Google Vertex AI.

Este módulo proporciona una función asíncrona para generar imágenes a partir de
una descripción textual (prompt) utilizando los modelos de generación de imágenes
de Vertex AI, como Imagen. Se encarga de la autenticación con Google Cloud,
la construcción de la petición a la API y el procesamiento de la respuesta.

Características Clave:
-   **Autenticación ADC:** Utiliza Application Default Credentials (ADC) para
    autenticarse de forma segura con Google Cloud, lo que es ideal para entornos
    de producción en GCP o para desarrollo local configurado con `gcloud auth`.
-   **Manejo de Respuesta Binaria:** La función devuelve un objeto `BytesIO` con
    los datos de la imagen en formato binario, listo para ser enviado a través
    de Telegram o guardado en disco, en lugar de solo la cadena base64.
-   **Detección de Relación de Aspecto:** Analiza el prompt en busca de palabras
    clave como "horizontal", "vertical" o "cuadrada" para ajustar automáticamente
    la relación de aspecto de la imagen generada.
-   **Configuración Centralizada:** Lee el ID del proyecto, la ubicación y el
    nombre del modelo desde el módulo `telegram_bot.config`, manteniendo toda la
    configuración en un solo lugar.
"""

import logging
import asyncio
import base64
import re
import json
from io import BytesIO
from typing import Union

import requests
import google.auth
import google.auth.transport.requests

# Importaciones del proyecto
from core.config import settings

# Configuración del logger para este módulo.
logger = logging.getLogger(__name__)

# Constante para la clave en user_data donde se guardará la imagen generada.
# Es utilizada por la herramienta de generación y el message_handler.
GENERATED_IMAGE_KEY = "generated_image_bytesio"


async def generar_imagen_vertex_ai_binario(description: str) -> Union[BytesIO, str]:
    """
    Realiza una petición a la API de Vertex AI para generar una imagen.

    Args:
        description: El prompt detallado para la generación de la imagen.

    Returns:
        Un objeto BytesIO con los datos de la imagen si tiene éxito,
        o una cadena de texto con un mensaje de error si falla.
    """
    try:
        # --- 1. Autenticación con Google Cloud ---
        # Obtiene las credenciales por defecto del entorno (gcloud, variables de entorno).
        logger.debug("Obteniendo credenciales de Google (ADC)...")
        credentials, project_id_from_auth = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
        auth_req = google.auth.transport.requests.Request()
        credentials.refresh(auth_req)  # Obtiene un token de acceso fresco.
        access_token = credentials.token
        logger.debug("Credenciales de Google obtenidas exitosamente.")

        # --- 2. Verificación y Construcción del Endpoint ---
        if not all([settings.google_project_id, settings.google_project_location, settings.google_image_generation_model_name]):
            error_msg = "Configuración de Vertex AI incompleta. Faltan GOOGLE_PROJECT_ID, GOOGLE_PROJECT_LOCATION o GOOGLE_IMAGE_GENERATION_MODEL_NAME."
            logger.error(f"❌ {error_msg}")
            return error_msg

        project_id = settings.google_project_id
        location = settings.google_project_location
        model_id = settings.google_image_generation_model_name
        
        endpoint = f"https://{location}-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{location}/publishers/google/models/{model_id}:predict"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
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
        
        if aspect_ratio_param:
            logger.info(f"Relación de aspecto detectada en el prompt: '{aspect_ratio_param}'")

        # --- 4. Construcción del Cuerpo de la Petición (Payload) ---
        data = {
            "instances": [{"prompt": description}],
            "parameters": {"sampleCount": 1}
        }
        if aspect_ratio_param:
            data["parameters"]["aspectRatio"] = aspect_ratio_param

        logger.debug(f"Enviando petición a Vertex AI. Endpoint: {endpoint}")
        logger.debug(f"Payload de la petición: {json.dumps(data, indent=2)}")

        # --- 5. Realizar la Petición HTTP ---
        # `requests.post` es una llamada síncrona, la ejecutamos en un hilo para no bloquear el bucle de asyncio.
        response = await asyncio.to_thread(
            requests.post,
            endpoint,
            headers=headers,
            data=json.dumps(data),
            timeout=180  # Timeout generoso para la generación de la imagen.
        )
        response.raise_for_status()  # Lanza una excepción para errores 4xx/5xx.
        resp_json = response.json()
        logger.debug(f"Respuesta recibida de Vertex AI: {json.dumps(resp_json, indent=2)}")

        # --- 6. Procesamiento de la Respuesta ---
        if "predictions" in resp_json and resp_json["predictions"]:
            prediction = resp_json["predictions"][0]
            if "bytesBase64Encoded" in prediction:
                image_base64 = prediction["bytesBase64Encoded"]
                image_bytes = base64.b64decode(image_base64)
                
                # Envolver los bytes de la imagen en un objeto BytesIO.
                bio = BytesIO(image_bytes)
                bio.name = 'generated_image.png'  # Asignar un nombre de archivo por defecto.
                
                logger.info("✅ Imagen generada y decodificada exitosamente desde Vertex AI.")
                return bio

        # Si no se encuentra la imagen en la respuesta esperada.
        error_detail = resp_json.get("error", {}).get("message", "La respuesta no contenía una imagen válida.")
        logger.error(f"❌ Respuesta inesperada de Vertex AI: {error_detail}")
        return f"Error: No se recibió la imagen en la respuesta de la API. Detalle: {error_detail}"

    except google.auth.exceptions.DefaultCredentialsError:
        error_msg = "Error de credenciales de Google. Asegúrate de haber ejecutado 'gcloud auth application-default login' o de tener configurada una cuenta de servicio en tu entorno."
        logger.error(f"❌ {error_msg}", exc_info=True)
        return error_msg
    except requests.exceptions.HTTPError as e:
        response_text = e.response.text if e.response else "Sin respuesta del servidor."
        logger.error(f"❌ Error HTTP a Vertex AI: {e}. Respuesta: {response_text}", exc_info=True)
        try:
            error_detail = e.response.json().get("error", {}).get("message", response_text)
            return f"Error al generar imagen: Fallo en la API. Detalle: {error_detail}"
        except json.JSONDecodeError:
            return f"Error al generar imagen: Fallo en la API con status {e.response.status_code}. Respuesta no es JSON."
    except Exception as e:
        logger.error(f"❌ Error inesperado al generar imagen con Vertex AI: {e}", exc_info=True)
        return f"Error inesperado al procesar la solicitud de imagen: {e}"
