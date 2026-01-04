# tools/table_analysis_tool.py

import logging
import uuid
import json
from typing import Optional, Dict, Any, List, Type
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
import httpx

from core.config import settings

logger = logging.getLogger(__name__)

class TableAnalysisInput(BaseModel):
    table_id: str = Field(..., description="El ID de la tabla a manipular.")
    action: str = Field(..., description="La acción a realizar: 'stats', 'predict', 'add_row', 'update_row', 'delete_row', 'update_columns'.")
    account_id: str = Field(..., description="El ID de la cuenta del usuario.")
    data: Optional[Dict[str, Any]] = Field(None, description="Datos para la fila (usar con 'add_row' o 'update_row').")
    row_id: Optional[str] = Field(None, description="ID de la fila (usar con 'update_row' o 'delete_row').")
    columns: Optional[List[Dict[str, Any]]] = Field(None, description="Lista de columnas (usar con 'update_columns'). Cada columna debe tener 'name' y 'type'.")
    x_col: Optional[str] = Field(None, description="Nombre de la columna independiente (X) para predicción.")
    y_col: Optional[str] = Field(None, description="Nombre de la columna dependiente (Y) para predicción.")

class TableAnalysisTool(BaseTool):
    name: str = "table_analysis_tool"
    description: str = (
        "Herramienta integral para analizar y editar tablas de datos. "
        "Permite obtener estadísticas, realizar predicciones, añadir/editar/eliminar filas y gestionar el esquema de columnas. "
        "Úsala para manipular datos estructurados del usuario al estilo de una hoja de cálculo."
    )
    args_schema: Type[BaseModel] = TableAnalysisInput
    
    api_url: str = "http://localhost:8000/api/tables"

    async def _arun(
        self, 
        table_id: str, 
        action: str,
        account_id: str,
        data: Optional[Dict[str, Any]] = None,
        row_id: Optional[str] = None,
        columns: Optional[List[Dict[str, Any]]] = None,
        x_col: Optional[str] = None,
        y_col: Optional[str] = None,
        **kwargs
    ) -> str:
        """Ejecuta la acción solicitada sobre la tabla."""
        try:
            async with httpx.AsyncClient() as client:
                headers = {"X-Account-Id": account_id} # Simulación de auth
                
                if action == "stats":
                    response = await client.get(f"{self.api_url}/{table_id}/analysis/stats", headers=headers)
                
                elif action == "predict":
                    if not x_col or not y_col:
                        return "Error: Se requieren x_col y y_col para realizar una predicción."
                    response = await client.get(f"{self.api_url}/{table_id}/analysis/predict", params={"x_col": x_col, "y_col": y_col}, headers=headers)
                
                elif action == "add_row":
                    if not data: return "Error: Se requieren 'data' para añadir una fila."
                    response = await client.post(f"{self.api_url}/{table_id}/rows", json={"data": data}, headers=headers)
                
                elif action == "update_row":
                    if not row_id or not data: return "Error: Se requieren 'row_id' y 'data' para actualizar una fila."
                    response = await client.patch(f"{self.api_url}/{table_id}/rows/{row_id}", json={"data": data}, headers=headers)
                
                elif action == "delete_row":
                    if not row_id: return "Error: Se requiere 'row_id' para eliminar una fila."
                    response = await client.delete(f"{self.api_url}/{table_id}/rows/{row_id}", headers=headers)
                
                elif action == "update_columns":
                    if not columns: return "Error: Se requieren 'columns' para actualizar el esquema."
                    response = await client.patch(f"{self.api_url}/{table_id}/columns", json=columns, headers=headers)
                
                else:
                    return f"Acción '{action}' no reconocida."

                if response.status_code in [200, 201]:
                    return f"Éxito en la acción '{action}':\n{json.dumps(response.json(), indent=2, ensure_ascii=False)}"
                elif response.status_code == 204:
                    return f"Éxito en la acción '{action}': Fila eliminada correctamente."
                else:
                    return f"Error en la acción '{action}': {response.status_code} - {response.text}"

        except Exception as e:
            logger.error(f"Error en TableAnalysisTool: {e}")
            return f"Error interno al ejecutar la herramienta: {str(e)}"

    def _run(self, *args, **kwargs):
        raise NotImplementedError("Esta herramienta solo soporta ejecución asíncrona.")
