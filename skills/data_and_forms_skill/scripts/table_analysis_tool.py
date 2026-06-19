import logging
import uuid
import json as json_module
from typing import Literal, Optional, Dict, Any, List, Type
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, validator, ValidationError
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from core.config import settings

logger = logging.getLogger(__name__)

ALLOWED_COLUMN_TYPES = {"string", "number", "boolean", "date"}
ALLOWED_ACTIONS = {"stats", "predict", "add_row", "update_row", "delete_row", "update_columns"}


class TableAnalysisInput(BaseModel):
    table_id: str = Field(..., description="El ID de la tabla a manipular (UUID).")
    action: Literal["stats", "predict", "add_row", "update_row", "delete_row", "update_columns"] = Field(
        ...,
        description="La acción a realizar: 'stats', 'predict', 'add_row', 'update_row', 'delete_row', 'update_columns'.",
    )
    account_id: str = Field(..., description="El ID de la cuenta del usuario (UUID).")
    data: Optional[Dict[str, Any]] = Field(
        None,
        description="Datos para la fila (usar con 'add_row' o 'update_row'). Las claves deben coincidir con nombres de columna.",
    )
    row_id: Optional[str] = Field(
        None,
        description="ID de la fila (UUID) (usar con 'update_row' o 'delete_row').",
    )
    columns: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Lista de columnas (usar con 'update_columns'). Cada columna debe tener 'name' (str) y 'type' (string|number|boolean|date).",
    )
    x_col: Optional[str] = Field(
        None,
        description="Nombre de la columna independiente (X) para predicción.",
    )
    y_col: Optional[str] = Field(
        None,
        description="Nombre de la columna dependiente (Y) para predicción.",
    )

    @validator("table_id", "account_id", "row_id", pre=True)
    def validate_uuid_fields(cls, v):
        if v is None:
            return v
        if not isinstance(v, str):
            raise ValueError("El campo debe ser un string representando un UUID.")
        try:
            uuid.UUID(v)
        except (ValueError, AttributeError):
            raise ValueError(f"El valor '{v}' no es un UUID válido.")
        return v

    @validator("data", pre=True)
    def parse_data(cls, v):
        if isinstance(v, str):
            try:
                parsed = json_module.loads(v)
                if not isinstance(parsed, dict):
                    raise ValueError("'data' debe ser un objeto JSON (dict).")
                return parsed
            except Exception as e:
                raise ValueError(f"No se pudo parsear 'data' como JSON: {e}")
        if v is not None and not isinstance(v, dict):
            raise ValueError("'data' debe ser un diccionario.")
        return v

    @validator("columns", pre=True)
    def validate_columns_structure(cls, v):
        if v is None:
            return v
        if not isinstance(v, list):
            raise ValueError("'columns' debe ser una lista.")
        for i, col in enumerate(v):
            if not isinstance(col, dict):
                raise ValueError(f"La columna #{i+1} debe ser un diccionario.")
            if "name" not in col:
                raise ValueError(f"La columna #{i+1} debe tener un campo 'name'.")
            if not isinstance(col["name"], str) or not col["name"].strip():
                raise ValueError(f"El 'name' de la columna #{i+1} debe ser un string no vacío.")
            col_type = col.get("type")
            if col_type is None:
                raise ValueError(f"La columna '{col['name']}' debe tener un campo 'type'.")
            if not isinstance(col_type, str) or col_type.lower() not in ALLOWED_COLUMN_TYPES:
                raise ValueError(
                    f"Tipo de columna inválido '{col_type}' para '{col['name']}'. "
                    f"Valores permitidos: {sorted(ALLOWED_COLUMN_TYPES)}."
                )
            col["type"] = col_type.lower()
        return v

    @validator("action")
    def validate_action(cls, v):
        if v not in ALLOWED_ACTIONS:
            raise ValueError(
                f"Acción '{v}' no reconocida. Acciones permitidas: {sorted(ALLOWED_ACTIONS)}."
            )
        return v


class TableAnalysisTool(BaseTool):
    name: str = "table_analysis_tool"
    description: str = (
        "Herramienta integral para analizar y editar tablas de datos. "
        "Permite obtener estadísticas, realizar predicciones, añadir/editar/eliminar filas y gestionar el esquema de columnas. "
        "Úsala para manipular datos estructurados del usuario al estilo de una hoja de cálculo."
    )
    args_schema: Type[BaseModel] = TableAnalysisInput

    api_url: str = Field(
        default_factory=lambda: getattr(settings, "TABLES_API_URL", "http://localhost:8000/api/tables"),
        description="URL base de la API de tablas.",
    )
    timeout: float = Field(default=30.0, description="Timeout en segundos para las peticiones HTTP.")
    max_retries: int = Field(default=2, description="Número máximo de reintentos para errores transitorios.")

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        reraise=True,
    )
    async def _request_with_retry(self, client: httpx.AsyncClient, method: str, url: str, **kwargs):
        kwargs.setdefault("timeout", self.timeout)
        return await client.request(method, url, **kwargs)

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
        **kwargs,
    ) -> str:
        """
        Ejecuta la acción solicitada sobre la tabla con validaciones robustas.
        """
        try:
            async with httpx.AsyncClient() as client:
                headers = {"X-Account-Id": account_id}
                url = f"{self.api_url.rstrip('/')}/{table_id}"

                if action == "stats":
                    response = await self._request_with_retry(
                        client, "GET", f"{url}/analysis/stats", headers=headers
                    )

                elif action == "predict":
                    missing = [name for name in ("x_col", "y_col") if not locals().get(name)]
                    if missing:
                        return f"Error: Se requieren {', '.join(missing)} para realizar una predicción."
                    response = await self._request_with_retry(
                        client,
                        "GET",
                        f"{url}/analysis/predict",
                        params={"x_col": x_col, "y_col": y_col},
                        headers=headers,
                    )

                elif action == "add_row":
                    if not data:
                        return "Error: Se requieren 'data' para añadir una fila."
                    response = await self._request_with_retry(
                        client, "POST", f"{url}/rows", json={"data": data}, headers=headers
                    )

                elif action == "update_row":
                    if not row_id:
                        return "Error: Se requiere 'row_id' para actualizar una fila."
                    if not data:
                        return "Error: Se requieren 'data' para actualizar una fila."
                    response = await self._request_with_retry(
                        client,
                        "PATCH",
                        f"{url}/rows/{row_id}",
                        json={"data": data},
                        headers=headers,
                    )

                elif action == "delete_row":
                    if not row_id:
                        return "Error: Se requiere 'row_id' para eliminar una fila."
                    response = await self._request_with_retry(
                        client, "DELETE", f"{url}/rows/{row_id}", headers=headers
                    )

                elif action == "update_columns":
                    if not columns:
                        return "Error: Se requieren 'columns' para actualizar el esquema."
                    response = await self._request_with_retry(
                        client, "PATCH", f"{url}/columns", json=columns, headers=headers
                    )

                else:
                    return f"Acción '{action}' no reconocida."

                # Manejo de respuestas HTTP
                if response.status_code in (200, 201):
                    try:
                        payload = response.json()
                    except Exception:
                        payload = {"raw": response.text}
                    return (
                        f"Éxito en la acción '{action}':\n"
                        f"{json_module.dumps(payload, indent=2, ensure_ascii=False)}"
                    )
                elif response.status_code == 204:
                    return f"Éxito en la acción '{action}': Operación completada sin contenido."
                elif response.status_code == 400:
                    return (
                        f"Error de validación en la acción '{action}' (400): "
                        f"{response.text}"
                    )
                elif response.status_code == 404:
                    return f"Error: Tabla o recurso no encontrado (404). Verifica table_id/row_id."
                elif response.status_code == 422:
                    return f"Error de datos en la acción '{action}' (422): {response.text}"
                else:
                    return (
                        f"Error en la acción '{action}': "
                        f"{response.status_code} - {response.text}"
                    )

        except ValidationError as e:
            logger.error(
                "Error de validación en TableAnalysisTool",
                extra={
                    "table_id": table_id,
                    "action": action,
                    "account_id": account_id,
                    "validation_errors": e.errors(),
                },
            )
            return f"Error de validación de parámetros: {e}"
        except httpx.TimeoutException:
            logger.error(
                "Timeout en TableAnalysisTool",
                extra={"table_id": table_id, "action": action, "account_id": account_id},
            )
            return "Error: La operación tardó demasiado tiempo. Intenta nuevamente."
        except httpx.NetworkError as e:
            logger.error(
                "Error de red en TableAnalysisTool",
                extra={"table_id": table_id, "action": action, "account_id": account_id, "error": str(e)},
            )
            return "Error de conexión con el servicio de tablas. Intenta nuevamente."
        except Exception as e:
            logger.exception(
                "Error interno en TableAnalysisTool",
                extra={"table_id": table_id, "action": action, "account_id": account_id},
            )
            return f"Error interno al ejecutar la herramienta: {str(e)}"

    def _run(self, *args, **kwargs):
        raise NotImplementedError("table_analysis_tool no soporta ejecución síncrona.")
