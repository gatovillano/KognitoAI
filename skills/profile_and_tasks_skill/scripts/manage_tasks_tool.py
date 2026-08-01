# skills/profile_and_tasks_skill/scripts/manage_tasks_tool.py

import logging
from typing import Any, Optional, Type, Dict, List
from datetime import datetime
import dateparser
import pytz

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from core.tasks_manager import TasksManager
from core.database import SessionLocal, Account
from utils.db_session import DBSession

logger = logging.getLogger(__name__)

class ManageTasksInput(BaseModel):
    """Esquema de entrada para la herramienta de gestión de tareas."""
    action: str = Field(..., description="Acción a realizar: 'create', 'update', 'complete', 'delete', 'list'")
    description: Optional[str] = Field(None, description="Descripción de la tarea (requerido para 'create' y 'update').")
    task_id: Optional[str] = Field(None, description="ID de la tarea (requerido para 'update', 'complete', 'delete').")
    start_time: Optional[str] = Field(None, description="Fecha/hora de inicio en lenguaje natural (ej: 'mañana a las 9am').")
    end_time: Optional[str] = Field(None, description="Fecha/hora de vencimiento en lenguaje natural (ej: 'viernes a las 6pm').")
    status: Optional[str] = Field(None, description="Estado de la tarea ('Pendiente', 'En Progreso', 'Hecho').")
    workspace_id: Optional[str] = Field(None, description="ID del workspace (opcional).")

class ManageTasksTool(BaseTool):
    name: str = "manage_tasks"
    description: str = (
        "🛠️ GESTOR DE TAREAS - Usa esta herramienta para crear, listar, actualizar, completar o eliminar tareas de la agenda. "
        "Las tareas son diferentes de los eventos; son elementos de acción con estado (pendiente/hecho). "
        "Puedes listar las tareas para obtener sus IDs y fechas, o fijar tanto el día como la hora de inicio y vencimiento."
    )
    args_schema: Type[BaseModel] = ManageTasksInput
    account_id: str = Field(..., description="Inyectado automáticamente.")

    async def _arun(
        self,
        action: str,
        description: Optional[str] = None,
        task_id: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        status: Optional[str] = None,
        workspace_id: Optional[str] = None,
        **kwargs: Any
    ) -> str:
        import uuid
        try:
            # Obtener zona horaria del usuario
            user_tz = pytz.utc
            async with DBSession(SessionLocal) as db:
                tasks_manager = TasksManager(db)
                account = await db.get(Account, self.account_id)
                if account and account.timezone:
                    try:
                        user_tz = pytz.timezone(account.timezone)
                    except:
                        pass

                def parse_time(time_str: Optional[str]) -> Optional[datetime]:
                    if not time_str:
                        return None
                    parsed = dateparser.parse(
                        time_str, 
                        settings={'RELATIVE_BASE': datetime.now(user_tz), 'RETURN_AS_TIMEZONE_AWARE': True}
                    )
                    if parsed:
                        return parsed.astimezone(pytz.utc)
                    return None

                if action == 'create':
                    if not description:
                        return "❌ Error: La descripción es requerida para crear una tarea."
                    
                    s_date = parse_time(start_time)
                    e_date = parse_time(end_time)
                    
                    new_task = await tasks_manager.create_task(
                        account_id=self.account_id,
                        description=description,
                        start_date=s_date,
                        end_date=e_date,
                        workspace_id=workspace_id,
                        status=status or 'Pendiente'
                    )
                    
                    res = f"✅ Tarea creada con éxito (ID: {new_task.id})."
                    if s_date:
                        res += f" Inicio: {s_date.astimezone(user_tz).strftime('%Y-%m-%d %H:%M')}."
                    if e_date:
                        res += f" Vencimiento: {e_date.astimezone(user_tz).strftime('%Y-%m-%d %H:%M')}."
                    return res

                elif action == 'list':
                    tasks = await tasks_manager.list_tasks(
                        account_id=self.account_id,
                        workspace_id=workspace_id,
                        status=status
                    )
                    if not tasks:
                        return "📋 No se encontraron tareas."

                    lines = [f"📋 Tareas encontradas ({len(tasks)}):"]
                    for t in tasks:
                        t_id = t.get("id")
                        desc_str = t.get("description", "Sin descripción")
                        st = t.get("status", "Pendiente")
                        comp = "✅ Completa" if t.get("is_completed") else f"⏳ {st}"

                        dates_str = []
                        if t.get("start_date"):
                            val = t.get("start_date")
                            try:
                                dt = datetime.fromisoformat(val)
                                dates_str.append(f"Inicio: {dt.astimezone(user_tz).strftime('%Y-%m-%d %H:%M')}")
                            except Exception:
                                dates_str.append(f"Inicio: {val}")
                        
                        venc_val = t.get("end_date") or t.get("due_date")
                        if venc_val:
                            try:
                                dt = datetime.fromisoformat(venc_val)
                                dates_str.append(f"Vencimiento: {dt.astimezone(user_tz).strftime('%Y-%m-%d %H:%M')}")
                            except Exception:
                                dates_str.append(f"Vencimiento: {venc_val}")

                        date_info = f" ({', '.join(dates_str)})" if dates_str else ""
                        lines.append(f"- ID: {t_id} | [{comp}] {desc_str}{date_info}")

                    return "\n".join(lines)

                elif action == 'update':
                    if not task_id:
                        return "❌ Error: El task_id es requerido para actualizar una tarea."
                    
                    updates = {}
                    if description: updates['description'] = description
                    if start_time: updates['start_date'] = parse_time(start_time)
                    if end_time: updates['end_date'] = parse_time(end_time)
                    if status: updates['status'] = status
                    if workspace_id: updates['workspace_id'] = workspace_id
                    
                    updated_task = await tasks_manager.update_task(
                        account_id=self.account_id,
                        task_id=uuid.UUID(task_id) if task_id else None,
                        **updates
                    )
                    return f"✅ Tarea {task_id} actualizada correctamente."

                elif action == 'complete':
                    if not task_id:
                        return "❌ Error: El task_id es requerido para completar una tarea."
                    
                    await tasks_manager.update_task(
                        account_id=self.account_id,
                        task_id=uuid.UUID(task_id) if task_id else None,
                        status='Hecho',
                        is_completed=True
                    )
                    return f"✅ Tarea {task_id} marcada como completada."

                elif action == 'delete':
                    if not task_id:
                        return "❌ Error: El task_id es requerido para eliminar una tarea."
                    
                    await tasks_manager.delete_task(
                        account_id=self.account_id,
                        task_id=uuid.UUID(task_id) if task_id else None
                    )
                    return f"✅ Tarea {task_id} eliminada."

                else:
                    return f"❌ Acción '{action}' no reconocida."

        except Exception as e:
            logger.error(f"Error en ManageTasksTool: {e}", exc_info=True)
            return f"❌ Error al gestionar la tarea: {str(e)}"

    def _run(self, *args, **kwargs) -> str:
        raise NotImplementedError("Use _arun instead.")
