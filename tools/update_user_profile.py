# tools/update_user_profile.py

"""
Herramienta de LangChain para actualizar el perfil persistente de un usuario.

Esta herramienta es fundamental para la personalización a largo plazo. Permite
al agente de IA guardar información clave sobre el usuario, como su nombre,
gustos, intereses o cualquier otro dato relevante que surja en la conversación.

La herramienta está diseñada para ser completamente agnóstica de la plataforma,
operando con el `account_id` universal. El LLM es responsable de extraer la
información pertinente de la conversación y proporcionar el `account_id`
correcto, asegurando que el perfil se actualice en la cuenta correcta.
"""

import logging
from typing import Any, Optional, Type

from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

# Importa la función de lógica de negocio desde el gestor de memoria.
from core.memory_manager import update_user_profile

# Configuración del logger para este módulo.
logger = logging.getLogger(__name__)


class ProfileUpdateInput(BaseModel):
    """
    Define el esquema de entrada para la herramienta de actualización de perfil.
    Valida que los argumentos necesarios, especialmente el `account_id`, sean proporcionados.
    """
    # El cambio más importante: requerimos el identificador universal.
    account_id: str = Field(
        ...,
        description="El identificador universal (UUID en formato string) de la cuenta del usuario. Debe ser proporcionado por el LLM."
    )
    # Los demás campos son opcionales, permitiendo actualizaciones parciales del perfil.
    nombre: Optional[str] = Field(default=None, description="El nombre del usuario.", json_schema_extra={"type": "string"})
    gustos: Optional[str] = Field(default=None, description="Los gustos o preferencias del usuario.", json_schema_extra={"type": "string"})
    intereses: Optional[str] = Field(default=None, description="Los intereses o hobbies del usuario.", json_schema_extra={"type": "string"})
    otros_datos: Optional[str] = Field(default=None, description="Cualquier otra información relevante sobre el usuario.", json_schema_extra={"type": "string"})


class UpdateProfileTool(BaseTool):
    """
    Una herramienta de LangChain que se conecta a la función `update_user_profile`
    para guardar o actualizar la información del perfil de un usuario en la base de datos.
    """
    name: str = "update_user_profile"
    description: str = (
        "Útil cuando el usuario proporciona información personal sobre sí mismo, como su nombre, gustos, "
        "intereses, ubicación, o cualquier otro detalle fáctico sobre su identidad o preferencias que deba "
        "ser recordado a largo plazo. Usa esta herramienta para guardar proactivamente esta información, "
        "incluso si el usuario no te pidió explícitamente que lo guardaras."
    )
    args_schema: Type[BaseModel] = ProfileUpdateInput
    return_direct: bool = False

    async def _arun(
        self,
        run_manager = None,
        **kwargs
    ) -> str:
        """
        Ejecuta la lógica de la herramienta de forma asíncrona.

        Args:
            account_id: El ID universal de la cuenta del usuario.
            nombre: El nombre del usuario a actualizar.
            gustos: Los gustos a actualizar.
            intereses: Los intereses a actualizar.
            otros_datos: Otros datos a actualizar.
        """
        # Extraer parámetros de kwargs
        nombre = kwargs.get('nombre')
        gustos = kwargs.get('gustos')
        intereses = kwargs.get('intereses')
        otros_datos = kwargs.get('otros_datos')

        # Obtener account_id del contexto de configuración o instancia
        account_id = None
        account_id_source = "unknown"
        
        # Intentar obtener del contexto del run_manager
        if run_manager and hasattr(run_manager, 'config'):
            config = getattr(run_manager, 'config', {})
            configurable = config.get('configurable', {})
            account_id = configurable.get('account_id')
            if account_id:
                account_id_source = "run_manager.config.configurable"
        
        # Fallback: obtener de la instancia
        if not account_id:
            account_id = getattr(self, 'account_id', "")
            if account_id:
                account_id_source = "self.account_id"

        # Validar que tenemos account_id
        if not account_id:
            return "Error: No se pudo obtener el account_id. Esta herramienta requiere identificación del usuario."

        logger.info(f"Ejecutando UpdateProfileTool para la cuenta '{account_id}'.")

        # Construir un diccionario solo con los datos que fueron proporcionados.
        # Esto evita sobreescribir campos existentes con None si no se especifican.
        update_data = {
            k: v for k, v in {
                "nombre": nombre,
                "gustos": gustos,
                "intereses": intereses,
                "otros_datos": otros_datos
            }.items() if v is not None
        }

        if not update_data:
            logger.warning(f"UpdateProfileTool fue llamada para la cuenta '{account_id}' pero no se proporcionaron datos para actualizar.")
            return "No se proporcionó información específica del perfil para actualizar."

        try:
            # Llama a la función de lógica de negocio, que ahora debe ser actualizada
            # para aceptar 'account_id' en lugar de 'telegram_id'.
            await update_user_profile(account_id=account_id, **update_data)
            logger.info(f"Perfil actualizado exitosamente para la cuenta '{account_id}'.")
            return "La información de tu perfil ha sido actualizada."
        except Exception as e:
            logger.error(f"Error en UpdateProfileTool para la cuenta '{account_id}': {e}", exc_info=True)
            return f"Ocurrió un error inesperado al actualizar tu perfil: {e}"

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """La ejecución síncrona no está soportada en nuestra arquitectura asíncrona."""
        raise NotImplementedError("update_user_profile no soporta ejecución síncrona.")