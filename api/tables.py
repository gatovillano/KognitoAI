# api/tables.py

import logging
import uuid
import json
import math
from typing import List, Optional, Any, Dict
from datetime import datetime, timezone
import pandas as pd
import io
from fastapi import APIRouter, HTTPException, Depends, status, Query, Body, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update
from pydantic import BaseModel, Field

from core.database import UserTable, UserTableRow, get_db_session
from utils.security import get_current_account_id
from utils.helpers import clean_nan_values

logger = logging.getLogger(__name__)

router = APIRouter()

# --- Modelos Pydantic ---

class ColumnSchema(BaseModel):
    name: str
    type: str  # string, number, boolean, date
    required: bool = False

class TableCreate(BaseModel):
    name: str
    description: Optional[str] = None
    columns: List[ColumnSchema]
    workspace_id: Optional[str] = None

class TableUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    columns: Optional[List[ColumnSchema]] = None

class TableResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    columns: List[ColumnSchema]
    workspace_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class RowCreate(BaseModel):
    data: Dict[str, Any]

class RowResponse(BaseModel):
    id: uuid.UUID
    table_id: uuid.UUID
    data: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# --- Endpoints de Tablas ---

@router.post("/", response_model=TableResponse, status_code=status.HTTP_201_CREATED)
async def create_table(
    table_data: TableCreate,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """Crea una nueva tabla personalizada."""
    try:
        new_table = UserTable(
            account_id=uuid.UUID(current_account_id),
            workspace_id=uuid.UUID(table_data.workspace_id) if table_data.workspace_id else None,
            name=table_data.name,
            description=table_data.description,
            columns=[col.dict() for col in table_data.columns]
        )
        db.add(new_table)
        await db.commit()
        await db.refresh(new_table)
        return new_table
    except Exception as e:
        logger.error(f"Error al crear tabla: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Error al crear la tabla.")

@router.get("/", response_model=List[TableResponse])
async def get_tables(
    workspace_id: Optional[str] = Query(None),
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """Obtiene todas las tablas del usuario o de un workspace."""
    stmt = select(UserTable).where(UserTable.account_id == uuid.UUID(current_account_id))
    if workspace_id:
        stmt = stmt.where(UserTable.workspace_id == uuid.UUID(workspace_id))
    
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/{table_id}", response_model=TableResponse)
async def get_table(
    table_id: uuid.UUID,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """Obtiene los detalles de una tabla específica."""
    stmt = select(UserTable).where(
        UserTable.id == table_id,
        UserTable.account_id == uuid.UUID(current_account_id)
    )
    result = await db.execute(stmt)
    table = result.scalar_one_or_none()
    if not table:
        raise HTTPException(status_code=404, detail="Tabla no encontrada.")
    return table

@router.delete("/{table_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_table(
    table_id: uuid.UUID,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """Elimina una tabla y todos sus registros."""
    stmt = select(UserTable).where(
        UserTable.id == table_id,
        UserTable.account_id == uuid.UUID(current_account_id)
    )
    result = await db.execute(stmt)
    table = result.scalar_one_or_none()
    if not table:
        raise HTTPException(status_code=404, detail="Tabla no encontrada.")
    
    await db.delete(table)
    await db.commit()
    return None

@router.patch("/{table_id}", response_model=TableResponse)
async def update_table(
    table_id: uuid.UUID,
    table_data: TableUpdate,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """Actualiza los metadatos de una tabla."""
    stmt = select(UserTable).where(
        UserTable.id == table_id,
        UserTable.account_id == uuid.UUID(current_account_id)
    )
    result = await db.execute(stmt)
    table = result.scalar_one_or_none()
    if not table:
        raise HTTPException(status_code=404, detail="Tabla no encontrada.")
    
    if table_data.name is not None:
        table.name = table_data.name
    if table_data.description is not None:
        table.description = table_data.description
    if table_data.columns is not None:
        table.columns = [col.dict() for col in table_data.columns]
    
    await db.commit()
    await db.refresh(table)
    return table

@router.patch("/{table_id}/columns", response_model=TableResponse)
async def update_table_columns(
    table_id: uuid.UUID,
    columns: List[ColumnSchema],
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """Actualiza el esquema de columnas de una tabla."""
    stmt = select(UserTable).where(
        UserTable.id == table_id,
        UserTable.account_id == uuid.UUID(current_account_id)
    )
    result = await db.execute(stmt)
    table = result.scalar_one_or_none()
    if not table:
        raise HTTPException(status_code=404, detail="Tabla no encontrada.")
    
    table.columns = [col.dict() for col in columns]
    await db.commit()
    await db.refresh(table)
    return table

@router.post("/{table_id}/rows", response_model=RowResponse, status_code=status.HTTP_201_CREATED)
async def add_row(
    table_id: uuid.UUID,
    row_data: RowCreate,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """Agrega una fila de datos a una tabla."""
    # Verificar propiedad de la tabla
    stmt = select(UserTable).where(
        UserTable.id == table_id,
        UserTable.account_id == uuid.UUID(current_account_id)
    )
    result = await db.execute(stmt)
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Tabla no encontrada.")
    
    new_row = UserTableRow(
        table_id=table_id,
        data=row_data.data
    )
    db.add(new_row)
    await db.commit()
    await db.refresh(new_row)
    return new_row

@router.get("/{table_id}/rows", response_model=List[RowResponse])
async def get_rows(
    table_id: uuid.UUID,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session),
    skip: int = 0,
    limit: int = 100
):
    """Obtiene las filas de una tabla con paginación."""
    # Verificar propiedad de la tabla
    stmt = select(UserTable).where(
        UserTable.id == table_id,
        UserTable.account_id == uuid.UUID(current_account_id)
    )
    result = await db.execute(stmt)
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Tabla no encontrada.")
    
    rows_stmt = select(UserTableRow).where(UserTableRow.table_id == table_id).offset(skip).limit(limit)
    rows_result = await db.execute(rows_stmt)
    return rows_result.scalars().all()

@router.patch("/{table_id}/rows/{row_id}", response_model=RowResponse)
async def update_row(
    table_id: uuid.UUID,
    row_id: uuid.UUID,
    row_data: RowCreate,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """Actualiza los datos de una fila específica."""
    # Verificar propiedad de la tabla
    stmt = select(UserTable).where(
        UserTable.id == table_id,
        UserTable.account_id == uuid.UUID(current_account_id)
    )
    result = await db.execute(stmt)
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Tabla no encontrada.")
    
    row_stmt = select(UserTableRow).where(
        UserTableRow.id == row_id,
        UserTableRow.table_id == table_id
    )
    row_result = await db.execute(row_stmt)
    row = row_result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Fila no encontrada.")
    
    row.data = row_data.data
    row.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(row)
    return row

@router.delete("/{table_id}/rows/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_row(
    table_id: uuid.UUID,
    row_id: uuid.UUID,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """Elimina una fila específica."""
    # Verificar propiedad de la tabla
    stmt = select(UserTable).where(
        UserTable.id == table_id,
        UserTable.account_id == uuid.UUID(current_account_id)
    )
    result = await db.execute(stmt)
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Tabla no encontrada.")
    
    row_stmt = select(UserTableRow).where(
        UserTableRow.id == row_id,
        UserTableRow.table_id == table_id
    )
    row_result = await db.execute(row_stmt)
    row = row_result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Fila no encontrada.")
    
    await db.delete(row)
    await db.commit()
    return None

@router.post("/import", response_model=TableResponse, status_code=status.HTTP_201_CREATED)
async def create_table_and_import(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    workspace_id: Optional[str] = Form(None),
    file: UploadFile = File(...),
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """Crea una nueva tabla e importa datos desde un archivo simultáneamente."""
    try:
        content = await file.read()
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(content))
        elif file.filename.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(io.BytesIO(content))
        else:
            raise HTTPException(status_code=400, detail="Formato de archivo no soportado. Use CSV o Excel.")

        # Reemplazar NaN por None para compatibilidad con JSON
        df = df.where(pd.notnull(df), None)
        
        # Generar esquema de columnas automáticamente basado en los datos
        columns = []
        for col_name in df.columns:
            dtype = str(df[col_name].dtype)
            col_type = "string"
            if "int" in dtype or "float" in dtype:
                col_type = "number"
            elif "bool" in dtype:
                col_type = "boolean"
            elif "datetime" in dtype:
                col_type = "date"
            
            columns.append({
                "name": str(col_name),
                "type": col_type,
                "required": False
            })

        # Manejar workspace_id cuando llega como cadena vacía desde el formulario
        actual_workspace_id = None
        if workspace_id and workspace_id.strip() and workspace_id != "undefined":
            try:
                actual_workspace_id = uuid.UUID(workspace_id)
            except ValueError:
                logger.warning(f"ID de workspace inválido: {workspace_id}. Se ignorará.")

        # Crear la tabla
        new_table = UserTable(
            account_id=uuid.UUID(current_account_id),
            workspace_id=actual_workspace_id,
            name=name,
            description=description,
            columns=columns
        )
        db.add(new_table)
        await db.flush() # Para obtener el ID de la tabla antes de insertar filas

        # Convertir a lista de diccionarios e insertar filas
        records = df.to_dict(orient='records')
        for record in records:
            # Asegurarse de que las claves sean strings y los valores compatibles
            clean_record = {str(k): v for k, v in record.items()}
            new_row = UserTableRow(
                table_id=new_table.id,
                data=clean_record
            )
            db.add(new_row)
        
        await db.commit()
        await db.refresh(new_table)
        return new_table
    except ImportError as e:
        logger.error(f"Falta dependencia para procesar el archivo: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=500, 
            detail="El servidor no tiene instaladas las dependencias necesarias para procesar este formato de archivo (ej: openpyxl)."
        )
    except Exception as e:
        logger.error(f"Error al crear e importar tabla: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al procesar el archivo: {str(e)}")


@router.post("/{table_id}/import", status_code=status.HTTP_201_CREATED)
async def import_data(
    table_id: uuid.UUID,
    file: UploadFile = File(...),
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """Importa datos desde un archivo CSV o Excel a una tabla."""
    # Verificar propiedad de la tabla
    stmt = select(UserTable).where(
        UserTable.id == table_id,
        UserTable.account_id == uuid.UUID(current_account_id)
    )
    result = await db.execute(stmt)
    table = result.scalar_one_or_none()
    if not table:
        raise HTTPException(status_code=404, detail="Tabla no encontrada.")
    
    try:
        content = await file.read()
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(content))
        elif file.filename.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(io.BytesIO(content))
        else:
            raise HTTPException(status_code=400, detail="Formato de archivo no soportado. Use CSV o Excel.")
        
        # Reemplazar NaN por None para compatibilidad con JSON
        df = df.where(pd.notnull(df), None)
        
        # Convertir a lista de diccionarios
        records = df.to_dict(orient='records')
        
        # Insertar filas
        for record in records:
            new_row = UserTableRow(
                table_id=table_id,
                data=record
            )
            db.add(new_row)
        
        await db.commit()
        return {"message": f"Se importaron {len(records)} filas exitosamente."}
    except Exception as e:
        logger.error(f"Error al importar datos: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al procesar el archivo: {str(e)}")

# --- Análisis de Datos ---

@router.get("/{table_id}/analysis/stats")
async def get_table_stats(
    table_id: uuid.UUID,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """Calcula estadísticas descriptivas básicas para las columnas numéricas."""
    # Verificar propiedad de la tabla
    stmt = select(UserTable).where(
        UserTable.id == table_id,
        UserTable.account_id == uuid.UUID(current_account_id)
    )
    result = await db.execute(stmt)
    table = result.scalar_one_or_none()
    if not table:
        raise HTTPException(status_code=404, detail="Tabla no encontrada.")
    
    # Obtener todas las filas
    rows_stmt = select(UserTableRow).where(UserTableRow.table_id == table_id)
    rows_result = await db.execute(rows_stmt)
    rows = rows_result.scalars().all()
    
    if not rows:
        return {"message": "No hay datos para analizar."}
    
    # Convertir a DataFrame
    df = pd.DataFrame([row.data for row in rows])
    
    # Identificar columnas numéricas
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    
    if not numeric_cols:
        return {"message": "No se encontraron columnas numéricas para análisis estadístico."}
    
    # Calcular estadísticas
    stats = df[numeric_cols].describe().to_dict()
    
    # Añadir correlaciones si hay más de una columna numérica
    correlations = {}
    if len(numeric_cols) > 1:
        correlations = df[numeric_cols].corr().to_dict()
    
    return {
        "statistics": clean_nan_values(stats),
        "correlations": clean_nan_values(correlations),
        "numeric_columns": numeric_cols
    }

@router.get("/{table_id}/analysis/predict")
async def get_table_prediction(
    table_id: uuid.UUID,
    x_col: str,
    y_col: str,
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """Realiza una regresión lineal simple entre dos columnas."""
    # Verificar propiedad de la tabla
    stmt = select(UserTable).where(
        UserTable.id == table_id,
        UserTable.account_id == uuid.UUID(current_account_id)
    )
    result = await db.execute(stmt)
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Tabla no encontrada.")
    
    # Obtener todas las filas
    rows_stmt = select(UserTableRow).where(UserTableRow.table_id == table_id)
    rows_result = await db.execute(rows_stmt)
    rows = rows_result.scalars().all()
    
    if not rows:
        return {"message": "No hay datos para analizar."}
    
    df = pd.DataFrame([row.data for row in rows])
    
    if x_col not in df.columns or y_col not in df.columns:
        raise HTTPException(status_code=400, detail="Columnas no encontradas.")
    
    # Eliminar filas con valores nulos en las columnas seleccionadas
    df_clean = df[[x_col, y_col]].dropna()
    
    if len(df_clean) < 2:
        return {"message": "No hay suficientes datos limpios para realizar una regresión."}
    
    try:
        from scipy import stats as scipy_stats
        slope, intercept, r_value, p_value, std_err = scipy_stats.linregress(df_clean[x_col], df_clean[y_col])
        
        return clean_nan_values({
            "slope": slope,
            "intercept": intercept,
            "r_squared": r_value**2 if not (math.isnan(r_value) if isinstance(r_value, float) or hasattr(r_value, 'dtype') else False) else None,
            "p_value": p_value,
            "std_err": std_err,
            "equation": f"y = {slope:.4f}x + {intercept:.4f}"
        })
    except Exception as e:
        logger.error(f"Error en análisis predictivo: {e}")
        raise HTTPException(status_code=500, detail="Error al calcular la regresión.")


# --- Análisis de IA ---

class TableAIAnalysisRequest(BaseModel):
    prompt: Optional[str] = None

@router.post("/{table_id}/analysis/ai")
async def analyze_table_with_ai(
    table_id: uuid.UUID,
    request_data: TableAIAnalysisRequest = Body(...),
    current_account_id: str = Depends(get_current_account_id),
    db: AsyncSession = Depends(get_db_session)
):
    """Genera un análisis e insights de la tabla utilizando un LLM."""
    # 1. Verificar propiedad de la tabla
    stmt = select(UserTable).where(
        UserTable.id == table_id,
        UserTable.account_id == uuid.UUID(current_account_id)
    )
    result = await db.execute(stmt)
    table = result.scalar_one_or_none()
    if not table:
        raise HTTPException(status_code=404, detail="Tabla no encontrada.")

    # 2. Obtener todas las filas de la tabla (límite razonable para evitar token limit)
    rows_stmt = select(UserTableRow).where(UserTableRow.table_id == table_id).limit(200)
    rows_result = await db.execute(rows_stmt)
    rows = rows_result.scalars().all()

    if not rows:
        return {"analysis": "No hay datos en la tabla para analizar."}

    # Convertir a DataFrame
    df = pd.DataFrame([row.data for row in rows])

    # 3. Calcular estadísticas descriptivas básicas para inyectar al prompt
    stats_summary = ""
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    if numeric_cols:
        stats_desc = df[numeric_cols].describe().to_string()
        stats_summary = f"\nEstadísticas descriptivas de las columnas numéricas:\n{stats_desc}\n"

    # Obtener primeras 30 filas como muestra en formato markdown o CSV
    data_sample = df.head(30).to_markdown(index=False)

    # 4. Formular el system prompt y human prompt
    system_prompt = (
        "Eres un analista de datos experto y asistente científico de IA. Tu tarea es analizar "
        "la tabla de datos proporcionada por el usuario, interpretar sus estadísticas y "
        "entregar un análisis descriptivo detallado, identificar patrones de interés, "
        "correlaciones implícitas, anomalías y dar recomendaciones prácticas.\n"
        "Presenta tu análisis con un formato Markdown profesional y limpio, usando títulos, "
        "negritas, listas y si es útil, tablas de resumen. Responde en español."
    )

    user_prompt = f"""Aquí tienes los detalles de la tabla de datos:
Nombre de la tabla: {table.name}
Descripción: {table.description or 'Sin descripción'}
Columnas configuradas: {json.dumps(table.columns, ensure_ascii=False)}

Muestra de los primeros 30 registros (formato tabla):
{data_sample}
{stats_summary}
Filas totales cargadas para análisis: {len(rows)} (mostrando hasta 200 en este contexto).

Objetivo/Instrucción específica del usuario:
{request_data.prompt or "Realiza un análisis general de los datos, resume los hallazgos principales, patrones interesantes y recomendaciones."}
"""

    try:
        from core.llm_manager import get_llm_for_user
        from langchain_core.messages import SystemMessage, HumanMessage

        llm = await get_llm_for_user(current_account_id)
        if not llm:
            raise HTTPException(status_code=500, detail="No se pudo inicializar el modelo de lenguaje.")

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]

        response = await llm.ainvoke(messages)
        return {"analysis": response.content}
    except Exception as e:
        logger.error(f"Error al analizar tabla con AI: {e}")
        raise HTTPException(status_code=500, detail=f"Error en el análisis de IA: {str(e)}")
