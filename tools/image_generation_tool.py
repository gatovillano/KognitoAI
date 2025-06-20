# tools/image_generation_tool.py

"""
Herramienta de LangChain para generar imágenes a partir de una descripción textual (prompt).

Esta herramienta permite al agente de IA crear contenido visual basado en las
peticiones del usuario. Se conecta a una función de generación de imágenes
(por ejemplo, a través de la API de Vertex AI o Gemini) y gestiona el resultado.

El diseño sigue la arquitectura centralizada y agnóstica de la plataforma:
1.  **Requiere `account_id`:** Aunque la generación de la imagen en sí no depende
    del usuario, el `account_id` podría usarse en el futuro para registrar el uso,
    aplicar estilos personalizados, etc. Mantiene la coherencia del diseño.
2.  **Requiere `telegram_id`:** Este es un caso especial. La herramienta no devuelve
    la imagen directamente. En su lugar, guarda la imagen (en formato BytesIO)
    en el `user_data` de la sesión de Telegram activa, usando el `telegram_id`
    como clave. El `message_handler` que inició la llamada al agente es responsable
    de revisar `user_data` y enviar la imagen al usuario. Este mecanismo de
    "paso de datos" a través del estado de la sesión es eficiente y evita
    transferir grandes blobs binarios a través de las capas del agente.
"""

import logging
from typing import Any, Type
from io import BytesIO

from pydantic.v1 import BaseModel, Field
from langchain_core.tools import BaseTool

# Importaciones de la lógica de negocio y gestión de estado
# La función que llama a la API de Vertex AI/Gemini
from utils.image_generation import generar_imagen_vertex_ai_binario 
# La clave donde se almacenará la imagen generada
from utils.image_generation_gemini import GENERATED_IMAGE_KEY 
# El gestor de estado de la sesión de Telegram
from telegram_client.bot_manager import bot_manager

# Configuración del logger para este módulo.
logger = logging.getLogger(__name__)


class ImageGenerationInput(BaseModel):
    """
    Define el esquema de entrada para la herramienta de generación de imágenes.
    Valida que el LLM proporcione todos los argumentos necesarios.
    """
    prompt: str = Field(
        ...,
        description="Una descripción detallada y clara de la imagen que se desea generar. Debería estar en inglés para obtener los mejores resultados."
    )
    # Requerimos ambos IDs por las razones explicadas en la documentación del módulo.
    account_id: str = Field(
        ...,
        description="El identificador universal (UUID en formato string) de la cuenta del usuario."
    )
    telegram_id: int = Field(
        ...,
        description="El ID numérico original de Telegram del usuario, necesario para guardar la imagen en el estado de la sesión (`user_data`)."
    )


class ImageGenerationTool(BaseTool):
    """
    Una herramienta de LangChain que se conecta a una API de generación de imágenes
    y gestiona la entrega del resultado a través del estado de la sesión del bot.
    """
    name: str = "generate_image_tool"
    description: str = (
        "Útil cuando el usuario te pide generar, crear, dibujar o visualizar una imagen "
        "basada en una descripción. Usa esta herramienta para cualquier petición que claramente "
        "pida una imagen o representación visual. El 'prompt' debe ser una descripción detallada "
        "de la imagen deseada."
    )
    args_schema: Type[BaseModel] = ImageGenerationInput
    return_direct: bool = False  # El agente debe procesar la respuesta.

    async def _arun(self, prompt: str, account_id: str, telegram_id: int, **kwargs: Any) -> str:
        """
        Ejecuta la lógica de la herramienta de forma asíncrona.

        Args:
            prompt: La descripción para generar la imagen.
            account_id: El ID universal de la cuenta del usuario.
            telegram_id: El ID de Telegram para la gestión del estado de sesión.
            **kwargs: Argumentos adicionales (no utilizados).

        Returns:
            Un mensaje de texto para el agente, indicando el resultado de la operación.
        """
        logger.info(f"Ejecutando ImageGenerationTool para la cuenta '{account_id}' con el prompt: '{prompt[:100]}...'")

        if not prompt or not prompt.strip():
            logger.warning(f"ImageGenerationTool llamada con un prompt vacío para la cuenta '{account_id}'.")
            return "Necesito una descripción para poder generar una imagen. ¿Qué te gustaría que creara?"

        try:
            # Llama a la función que realmente se conecta con la API de generación.
            image_result = await generar_imagen_vertex_ai_binario(prompt)

            if isinstance(image_result, BytesIO):
                # Si la generación fue exitosa, el resultado es un objeto BytesIO.
                # Lo guardamos en user_data usando el telegram_id como clave.
                user_data = bot_manager.get_user_data(telegram_id)
                user_data[GENERATED_IMAGE_KEY] = image_result
                await bot_manager.flush_persistence() # Asegura que se guarde el estado.
                
                logger.info(f"✅ Imagen generada y guardada en user_data para el usuario de Telegram {telegram_id}.")
                
                # Devolvemos un mensaje para que el agente se lo diga al usuario.
                return "¡Hecho! He generado la imagen y te la enviaré en un momento."
            else:
                # Si no es BytesIO, es un mensaje de error de la función de generación.
                error_message = str(image_result)
                logger.error(f"❌ La generación de imagen falló para la cuenta '{account_id}'. Razón: {error_message}")
                return f"No pude generar la imagen. El servicio de imágenes devolvió un error: {error_message}"

        except Exception as e:
            logger.error(f"Error en ImageGenerationTool para la cuenta '{account_id}': {e}", exc_info=True)
            return f"Ocurrió un error inesperado al intentar generar la imagen: {e}"

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """La ejecución síncrona no está soportada en nuestra arquitectura asíncrona."""
        raise NotImplementedError("generate_image_tool no soporta ejecución síncrona.")