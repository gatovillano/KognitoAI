import logging
import asyncio
from typing import Type, Any, Optional, List, Dict
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

from core.database import SessionLocal, FormResponse, Form
from utils.db_session import DBSession
from sqlalchemy import select
import uuid

logger = logging.getLogger(__name__)

class GetFormResponsesInput(BaseModel):
    form_name: Optional[str] = Field(None, description="El nombre exacto del formulario del cual se desean obtener las respuestas.")
    form_id: Optional[str] = Field(None, description="El ID único del formulario del cual se desean obtener las respuestas.")
    response_id: Optional[str] = Field(None, description="El ID único de una respuesta específica del formulario.")
    limit: int = Field(5, description="El número máximo de respuestas a devolver.")

class GetFormResponsesTool(BaseTool):
    name: str = "get_form_responses_tool"
    description: str = (
        "Útil para cuando el usuario quiere obtener las respuestas de un formulario. "
        "Permite buscar respuestas por el nombre o ID del formulario, o por el ID de una respuesta específica. "
        "Si no se especifica un formulario, se listarán las respuestas de los formularios más recientes. "
        "Devuelve las respuestas en formato legible, incluyendo el contenido de cada campo."
    )
    args_schema: Type[BaseModel] = GetFormResponsesInput
    account_id: str = Field(..., description="El ID de cuenta del usuario, inyectado automáticamente.")
    workspace_id: Optional[str] = Field(None, description="El ID del espacio de trabajo del usuario, inyectado automáticamente.")
    
    async def _arun(
        self,
        form_name: Optional[str] = None,
        form_id: Optional[str] = None,
        response_id: Optional[str] = None,
        limit: int = 5,
        **kwargs: Any,
    ) -> str:
        logger.info(f"Ejecutando GetFormResponsesTool para account_id='{self.account_id}' con form_name='{form_name}', form_id='{form_id}', response_id='{response_id}'.")

        if not self.account_id:
            return "Error: Se requiere el ID de la cuenta para obtener las respuestas del formulario."

        async with DBSession(SessionLocal) as db:
            account_uuid = uuid.UUID(self.account_id)
            
            # Si se proporciona un response_id, buscar esa respuesta específica
            if response_id:
                try:
                    response_uuid = uuid.UUID(response_id)
                    stmt = select(FormResponse).where(
                        FormResponse.id == response_uuid,
                        FormResponse.account_id == account_uuid
                    )
                    if self.workspace_id:
                        stmt = stmt.where(FormResponse.workspace_id == uuid.UUID(self.workspace_id))
                    
                    result = await db.execute(stmt)
                    response = result.scalars().first()

                    if response:
                        return self._format_single_response(response)
                    else:
                        return f"No se encontró ninguna respuesta con el ID '{response_id}'."
                except ValueError:
                    return f"Error: El ID de respuesta '{response_id}' no es un UUID válido."
            
            # Buscar el formulario por nombre o ID
            target_form: Optional[Form] = None
            if form_id:
                try:
                    form_uuid = uuid.UUID(form_id)
                    stmt = select(Form).where(
                        Form.id == form_uuid,
                        Form.account_id == account_uuid
                    )
                    if self.workspace_id:
                        stmt = stmt.where(Form.workspace_id == uuid.UUID(self.workspace_id))
                    
                    result = await db.execute(stmt)
                    target_form = result.scalars().first()
                except ValueError:
                    return f"Error: El ID de formulario '{form_id}' no es un UUID válido."
            elif form_name:
                stmt = select(Form).where(
                    Form.name == form_name,
                    Form.account_id == account_uuid
                )
                if self.workspace_id:
                    stmt = stmt.where(Form.workspace_id == uuid.UUID(self.workspace_id))
                
                result = await db.execute(stmt)
                target_form = result.scalars().first()

            if target_form:
                # Obtener respuestas para el formulario encontrado
                responses_stmt = select(FormResponse).where(
                    FormResponse.form_id == target_form.id,
                    FormResponse.account_id == account_uuid
                ).order_by(FormResponse.created_at.desc()).limit(limit)
                
                responses_result = await db.execute(responses_stmt)
                responses = responses_result.scalars().all()

                if responses:
                    formatted_responses = [self._format_single_response(res) for res in responses]
                    return f"Respuestas para el formulario '{target_form.name}' (ID: {target_form.id}):\n\n" + "\n---\n".join(formatted_responses)
                else:
                    return f"No se encontraron respuestas para el formulario '{target_form.name}'."
            else:
                # Si no se especificó un formulario, listar los formularios más recientes y sus respuestas
                forms_stmt = select(Form).where(
                    Form.account_id == account_uuid
                ).order_by(Form.created_at.desc()).limit(limit)
                
                if self.workspace_id:
                    forms_stmt = forms_stmt.where(Form.workspace_id == uuid.UUID(self.workspace_id))
                
                forms_result = await db.execute(forms_stmt)
                recent_forms = forms_result.scalars().all()

                if recent_forms:
                    response_message = "Aquí están los formularios más recientes y algunas de sus respuestas:\n\n"
                    for form in recent_forms:
                        responses_stmt = select(FormResponse).where(
                            FormResponse.form_id == form.id,
                            FormResponse.account_id == account_uuid
                        ).order_by(FormResponse.created_at.desc()).limit(2) # Mostrar 2 respuestas por formulario
                        
                        responses_result = await db.execute(responses_stmt)
                        responses = responses_result.scalars().all()

                        response_message += f"**Formulario: {form.name}** (ID: {form.id})\n"
                        if form.description:
                            response_message += f"  Descripción: {form.description}\n"
                        if responses:
                            for res in responses:
                                response_message += f"  - Respuesta (ID: {res.id}, Fecha: {res.created_at.strftime('%Y-%m-%d %H:%M')}):\n"
                                for field_name, field_value in res.response_data.items():
                                    response_message += f"    • {field_name}: {field_value}\n"
                        else:
                            response_message += "  No hay respuestas para este formulario.\n"
                        response_message += "\n"
                    return response_message
                else:
                    return "No tienes ningún formulario creado en tu base de conocimiento."

    def _format_single_response(self, response: FormResponse) -> str:
        formatted_data = "\n".join([f"    • {field_name}: {field_value}" for field_name, field_value in response.response_data.items()])
        return (
            f"Respuesta (ID: {response.id}, Fecha: {response.created_at.strftime('%Y-%m-%d %H:%M')}):\n"
            f"{formatted_data}"
        )

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("get_form_responses_tool no soporta ejecución síncrona.")