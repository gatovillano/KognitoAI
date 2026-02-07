# tools/create_table_tool.py

import logging
import uuid
from typing import Type, Any, Optional, List, Dict
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

from core.database import SessionLocal, UserTable, UserTableRow
from utils.db_session import DBSession

logger = logging.getLogger(__name__)

class ColumnSchema(BaseModel):
    name: str = Field(..., description="Nombre de la columna")
    type: str = Field(..., description="Tipo de dato: string, number, boolean, date")
    required: bool = False

class CreateTableInput(BaseModel):
    name: str = Field(..., description="Nombre de la tabla")
    description: Optional[str] = Field(None, description="Descripción de la tabla")
    columns: List[ColumnSchema] = Field(..., description="Lista de columnas de la tabla. Cada columna debe tener 'name' y 'type' (string, number, boolean, date).")
    workspace_id: Optional[str] = Field(None, description="ID del espacio de trabajo del usuario.")
    initial_rows: Optional[List[Dict[str, Any]]] = Field(None, description="Opcional: Lista de filas iniciales para insertar en la tabla. Las claves deben coincidir con los nombres de las columnas.")

class CreateTableTool(BaseTool):
    name: str = "create_table"
    description: str = "Crea una nueva tabla personalizada en la base de datos con un esquema definido. Útil para organizar datos estructurados y listas."
    args_schema: Type[BaseModel] = CreateTableInput
    account_id: str
    workspace_id: Optional[str] = Field(None, description="El ID del espacio de trabajo del usuario.")

    async def _arun(
        self,
        name: str,
        columns: List[ColumnSchema],
        description: Optional[str] = None,
        workspace_id: Optional[str] = None,
        initial_rows: Optional[List[Dict[str, Any]]] = None,
        **kwargs: Any,
    ) -> str:
        if not self.account_id:
            return "Error: Se requiere el ID de la cuenta para crear una tabla."

        # Usar el workspace_id pasado en los argumentos si está disponible, de lo contrario usar el inicializado
        final_workspace_id = workspace_id or self.workspace_id

        try:
            async with DBSession(SessionLocal) as session:
                new_table = UserTable(
                    account_id=uuid.UUID(self.account_id),
                    workspace_id=uuid.UUID(final_workspace_id) if final_workspace_id else None,
                    name=name,
                    description=description,
                    columns=[col.dict() for col in columns]
                )
                session.add(new_table)
                # Flush para obtener el ID de la tabla antes de insertar filas
                await session.flush()
                
                rows_added = 0
                if initial_rows:
                    for row_data in initial_rows:
                        # Asegurarnos de que las claves sean strings
                        clean_data = {str(k): v for k, v in row_data.items()}
                        new_row = UserTableRow(
                            table_id=new_table.id,
                            data=clean_data
                        )
                        session.add(new_row)
                        rows_added += 1

                await session.commit()
                await session.refresh(new_table)
                
                msg = f"✅ Tabla '{name}' creada exitosamente con ID {new_table.id}."
                if rows_added > 0:
                    msg += f" Se insertaron {rows_added} filas iniciales."
                return msg

        except Exception as e:
            logger.error(f"Error en CreateTableTool para la cuenta {self.account_id}: {e}", exc_info=True)
            return f"Ocurrió un error al intentar crear la tabla: {e}"

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("create_table_tool no soporta ejecución síncrona.")
