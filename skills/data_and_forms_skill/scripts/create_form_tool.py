# skills/data_and_forms_skill/scripts/create_form_tool.py

import logging
import uuid
import asyncio
from typing import Type, Any, Optional, List, Dict, Union, Literal
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

from core.database import SessionLocal, Form as DBForm
from utils.db_session import DBSession
from sqlalchemy import select

logger = logging.getLogger(__name__)

class FormFieldSchema(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="ID único del campo (se genera automáticamente si no se provee).")
    label: str = Field(..., description="Etiqueta o pregunta del campo.")
    description: Optional[str] = Field(None, description="Descripción opcional del campo.")
    type: Literal['text', 'checkbox', 'textarea', 'select', 'radio'] = Field(..., description="Tipo de campo.")
    options: Optional[List[str]] = Field(None, description="Lista de opciones para tipos 'select' o 'radio'.")
    is_required: bool = Field(False, description="Indica si el campo es obligatorio.")

class FormSectionSchema(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="ID único de la sección.")
    title: str = Field(..., description="Título de la sección.")
    description: Optional[str] = Field(None, description="Descripción opcional de la sección.")
    elements: List[Union[FormFieldSchema, 'FormSectionSchema']] = Field(default_factory=list, description="Lista de elementos (campos o subsecciones) dentro de esta sección.")

# Resolver la referencia circular para FormSectionSchema
FormSectionSchema.update_forward_refs()

class CreateFormInput(BaseModel):
    name: str = Field(..., description="Nombre del formulario.")
    description: Optional[str] = Field(None, description="Descripción del formulario.")
    elements: List[Union[FormFieldSchema, FormSectionSchema]] = Field(..., description="Lista de elementos (campos o secciones) que componen el formulario.")
    is_public: bool = Field(False, description="Indica si el formulario será público.")

class CreateFormTool(BaseTool):
    name: str = "create_form"
    description: str = (
        "Crea un nuevo formulario dinámico. Útil para recolectar información de usuarios o clientes. "
        "Permite definir campos (texto, checkbox, select, etc.) y secciones para organizar las preguntas. "
        "El formulario creado será visible en la interfaz de usuario en /forms."
    )
    args_schema: Type[BaseModel] = CreateFormInput
    account_id: str = Field(..., description="El ID de cuenta del usuario, inyectado automáticamente.")
    workspace_id: Optional[str] = Field(None, description="El ID del espacio de trabajo del usuario, inyectado automáticamente.")

    async def _arun(
        self,
        name: str,
        elements: List[Union[FormFieldSchema, FormSectionSchema]],
        description: Optional[str] = None,
        is_public: bool = False,
        **kwargs: Any,
    ) -> str:
        logger.info(f"Ejecutando CreateFormTool para account_id='{self.account_id}' con nombre='{name}', workspace_id='{self.workspace_id}'.")

        if not self.account_id:
            return "Error: Se requiere el ID de la cuenta para crear un formulario."

        try:
            async with DBSession(SessionLocal) as db:
                account_uuid = uuid.UUID(self.account_id)
                workspace_uuid = uuid.UUID(self.workspace_id) if self.workspace_id else None
                
                # Serializar los elementos de forma recursiva
                serialized_elements = self._serialize_elements(elements)
                
                new_form = DBForm(
                    account_id=account_uuid,
                    workspace_id=workspace_uuid,
                    name=name,
                    description=description,
                    schema=serialized_elements,
                    is_public=is_public
                )
                
                db.add(new_form)
                await db.commit()
                await db.refresh(new_form)
                
                return f"✅ Formulario '{name}' creado exitosamente con ID: {new_form.id}. Puedes verlo en la sección de formularios."

        except Exception as e:
            logger.error(f"Error al crear el formulario: {e}", exc_info=True)
            return f"Error al crear el formulario: {str(e)}"

    def _serialize_elements(self, elements: List[Union[FormFieldSchema, FormSectionSchema]]) -> List[Dict[str, Any]]:
        serialized = []
        for element in elements:
            if isinstance(element, FormFieldSchema):
                serialized.append(element.model_dump())
            elif isinstance(element, FormSectionSchema):
                item = element.model_dump()
                item['elements'] = self._serialize_elements(element.elements)
                serialized.append(item)
        return serialized

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("create_form_tool no soporta ejecución síncrona.")
