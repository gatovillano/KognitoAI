from typing import Union, Optional
from pydantic import BaseModel, Field
import asyncio
import json
from sqlalchemy import text
from core.database import SessionLocal
from utils.db_session import DBSession
from langchain.tools import BaseTool

class AnalysisResultsInput(BaseModel):
    """Esquema de entrada para obtener resultados de análisis."""
    account_id: str = Field(..., description="El identificador de la cuenta del usuario")
    analysis_type: Optional[str] = Field(None, description="Tipo de análisis: document, collection, semantic, code, proactive_insight, etc.")
    status: Optional[str] = Field(None, description="Estado del análisis: completed, pending, failed")
    limit: Optional[int] = Field(20, description="Número máximo de resultados a devolver")
    include_payload: Optional[bool] = Field(True, description="Si incluir el payload completo del resultado")

class AnalysisResultsTool(BaseTool):
    """
    Herramienta para obtener resultados de análisis almacenados en analysis_tasks.
    
    Permite filtrar por tipo de análisis, estado y obtener estadísticas de uso.
    Utiliza la nueva columna analysis_type para filtrado eficiente.
    """
    name: str = "get_analysis_results"
    description: str = (
        "Obtiene resultados de análisis almacenados en la base de datos. "
        "Permite filtrar por tipo de análisis (document, collection, semantic, code, etc.), "
        "estado (completed, pending, failed) y obtener estadísticas de uso. "
        "Útil para mostrar historial de análisis y resultados previos al usuario."
    )
    args_schema = AnalysisResultsInput

    def _run(
        self,
        account_id: str,
        analysis_type: Union[str, None] = None,
        status: Union[str, None] = None,
        limit: Union[int, None] = 20,
        include_payload: Union[bool, None] = True,
    ) -> str:
        """Obtiene resultados de análisis."""
        return asyncio.run(self._arun(
            account_id, analysis_type, status, limit, include_payload
        ))

    async def _arun(
        self,
        account_id: str,
        analysis_type: Union[str, None] = None,
        status: Union[str, None] = None,
        limit: Union[int, None] = 20,
        include_payload: Union[bool, None] = True,
    ) -> str:
        """Versión asíncrona para obtener resultados de análisis."""
        try:
            async with DBSession(SessionLocal) as session:
                # Construir consulta base
                query = """
                    SELECT 
                        id,
                        file_name,
                        analysis_type,
                        status,
                        created_at,
                        updated_at,
                        result_payload
                    FROM analysis_tasks
                    WHERE account_id = :account_id
                """
                
                params = {"account_id": account_id}
                
                # Agregar filtros opcionales
                if analysis_type:
                    query += " AND analysis_type = :analysis_type"
                    params["analysis_type"] = analysis_type
                
                if status:
                    query += " AND status = :status"
                    params["status"] = status
                
                # Ordenar por fecha de creación (más recientes primero)
                query += " ORDER BY created_at DESC"
                
                if limit:
                    query += " LIMIT :limit"
                    params["limit"] = str(limit)
                
                # Ejecutar consulta
                result = await session.execute(text(query), params)
                rows = result.fetchall()
                
                # Procesar resultados
                analysis_results = []
                for row in rows:
                    analysis_result = {
                        "id": str(row[0]),
                        "file_name": row[1],
                        "analysis_type": row[2],
                        "status": row[3],
                        "created_at": row[4].isoformat() if row[4] else None,
                        "updated_at": row[5].isoformat() if row[5] else None,
                    }
                    
                    # Incluir payload si se solicita
                    if include_payload and row[6]:
                        analysis_result["result_payload"] = row[6]
                    
                    analysis_results.append(analysis_result)
                
                # Obtener estadísticas por tipo
                stats_query = """
                    SELECT 
                        analysis_type,
                        COUNT(*) as total,
                        COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
                        COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending,
                        COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed
                    FROM analysis_tasks
                    WHERE account_id = :account_id
                    GROUP BY analysis_type
                    ORDER BY total DESC
                """
                
                stats_result = await session.execute(text(stats_query), {"account_id": account_id})
                stats_rows = stats_result.fetchall()
                
                statistics = []
                for stats_row in stats_rows:
                    statistics.append({
                        "analysis_type": stats_row[0],
                        "total": stats_row[1],
                        "completed": stats_row[2],
                        "pending": stats_row[3],
                        "failed": stats_row[4]
                    })
                
                return json.dumps({
                    "status": "success",
                    "total_results": len(analysis_results),
                    "filters_applied": {
                        "analysis_type": analysis_type,
                        "status": status,
                        "limit": limit
                    },
                    "statistics": statistics,
                    "results": analysis_results
                }, ensure_ascii=False, indent=2)
                
        except Exception as e:
            return json.dumps({
                "status": "error",
                "error": str(e),
                "account_id": account_id
            }, ensure_ascii=False)


class AnalysisTypesInput(BaseModel):
    """Esquema de entrada para obtener tipos de análisis disponibles."""
    account_id: str = Field(..., description="El identificador de la cuenta del usuario")

class AnalysisTypesTool(BaseTool):
    """
    Herramienta para obtener los tipos de análisis disponibles y sus estadísticas.
    """
    name: str = "get_analysis_types"
    description: str = (
        "Obtiene los tipos de análisis disponibles en el sistema y sus estadísticas de uso. "
        "Muestra cuántos análisis de cada tipo ha realizado el usuario y sus estados. "
        "Útil para mostrar al usuario qué tipos de análisis están disponibles."
    )
    args_schema = AnalysisTypesInput

    def _run(self, account_id: str) -> str:
        """Obtiene tipos de análisis disponibles."""
        return asyncio.run(self._arun(account_id))

    async def _arun(self, account_id: str) -> str:
        """Versión asíncrona para obtener tipos de análisis."""
        try:
            # Definir tipos de análisis disponibles con descripciones
            available_types = {
                "document": {
                    "name": "Análisis de Documentos",
                    "description": "Análisis de documentos individuales (PDFs, docs, etc.)",
                    "tools": ["advanced_text_analyzer.py"]
                },
                "collection": {
                    "name": "Análisis de Colecciones", 
                    "description": "Análisis de colecciones completas de documentos",
                    "tools": ["advanced_text_analyzer.py (colección)"]
                },
                "semantic": {
                    "name": "Análisis Semántico",
                    "description": "Análisis semántico de topics y clustering",
                    "tools": ["semantic_topic_analysis_tool.py"]
                },
                "code": {
                    "name": "Análisis de Código",
                    "description": "Análisis de código y repositorios",
                    "tools": ["advanced_code_analyzer.py"]
                },
                "proactive_insight": {
                    "name": "Insights Proactivos",
                    "description": "Insights proactivos automáticos",
                    "tools": ["proactive_knowledge_linker_tool.py"]
                },
                "conversation_context": {
                    "name": "Análisis de Contexto",
                    "description": "Análisis de contexto de conversaciones",
                    "tools": ["conversation_context_analyzer_tool.py"]
                },
                "conversation_history": {
                    "name": "Análisis de Historial",
                    "description": "Análisis de historial de conversaciones",
                    "tools": ["conversation_history_analyzer_tool.py"]
                },
                "knowledge_base": {
                    "name": "Análisis de Base de Conocimiento",
                    "description": "Análisis profundo de base de conocimiento",
                    "tools": ["knowledge_analysis_tool.py"]
                },
                "scoped_rag": {
                    "name": "Análisis RAG Focalizado",
                    "description": "Análisis RAG focalizado",
                    "tools": ["scoped_rag_analysis_tool.py"]
                },
                "web_analysis": {
                    "name": "Análisis Web",
                    "description": "Análisis web comprehensivo",
                    "tools": ["comprehensive_web_analysis_tool.py"]
                },
                "text_insights": {
                    "name": "Insights de Texto",
                    "description": "Análisis de texto para insights",
                    "tools": ["analyze_text_for_insights_tool.py"]
                },
                "code_insights": {
                    "name": "Insights de Código",
                    "description": "Análisis de código para insights",
                    "tools": ["analyze_code_for_insights_tool.py"]
                }
            }
            
            async with DBSession(SessionLocal) as session:
                # Obtener estadísticas de uso del usuario
                stats_query = """
                    SELECT 
                        analysis_type,
                        COUNT(*) as total,
                        COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
                        COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending,
                        COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed,
                        MAX(created_at) as last_used
                    FROM analysis_tasks
                    WHERE account_id = :account_id
                    GROUP BY analysis_type
                    ORDER BY total DESC
                """
                
                result = await session.execute(text(stats_query), {"account_id": account_id})
                rows = result.fetchall()
                
                # Combinar información de tipos disponibles con estadísticas de uso
                types_with_stats = []
                used_types = set()
                
                for row in rows:
                    analysis_type = row[0]
                    used_types.add(analysis_type)
                    
                    type_info = available_types.get(analysis_type, {
                        "name": analysis_type.title(),
                        "description": f"Análisis de tipo {analysis_type}",
                        "tools": ["unknown"]
                    })
                    
                    types_with_stats.append({
                        "type": analysis_type,
                        "name": type_info["name"],
                        "description": type_info["description"],
                        "tools": type_info["tools"],
                        "usage_stats": {
                            "total": row[1],
                            "completed": row[2],
                            "pending": row[3],
                            "failed": row[4],
                            "last_used": row[5].isoformat() if row[5] else None
                        }
                    })
                
                # Agregar tipos disponibles que no han sido usados
                for analysis_type, type_info in available_types.items():
                    if analysis_type not in used_types:
                        types_with_stats.append({
                            "type": analysis_type,
                            "name": type_info["name"],
                            "description": type_info["description"],
                            "tools": type_info["tools"],
                            "usage_stats": {
                                "total": 0,
                                "completed": 0,
                                "pending": 0,
                                "failed": 0,
                                "last_used": None
                            }
                        })
                
                return json.dumps({
                    "status": "success",
                    "total_types": len(types_with_stats),
                    "types_used": len(used_types),
                    "types_available": len(available_types),
                    "analysis_types": types_with_stats
                }, ensure_ascii=False, indent=2)
                
        except Exception as e:
            return json.dumps({
                "status": "error",
                "error": str(e),
                "account_id": account_id
            }, ensure_ascii=False)
