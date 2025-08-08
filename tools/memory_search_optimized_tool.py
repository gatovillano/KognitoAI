from typing import Union, Type, Optional
from pydantic import BaseModel, Field
import asyncio
import json
from core.memory_manager import create_memory_context, search_vector_db_optimized
from langchain_core.tools import BaseTool

class MemorySearchOptimizedInput(BaseModel):
    """Esquema de entrada para la herramienta de búsqueda optimizada de memoria."""
    query: str = Field(..., description="La consulta de búsqueda")
    content_type: Optional[str] = Field(None, description="Tipo de contenido: user_memories, user_documents, team_memories, team_documents", json_schema_extra={"type": "string"})
    topic: Optional[str] = Field(None, description="Topic organizacional específico del usuario", json_schema_extra={"type": "string"})
    category: Optional[str] = Field(None, description="Categoría automática del LLM", json_schema_extra={"type": "string"})
    k: Optional[int] = Field(10, description="Número máximo de resultados a devolver", json_schema_extra={"type": "integer"})
    include_shared: Union[bool, None] = Field(True, description="Si incluir contenido compartido con teams", json_schema_extra={"type": "boolean"})

class MemorySearchOptimizedTool(BaseTool):
    """
    Herramienta optimizada para búsqueda en memoria vectorial.
    
    Utiliza las nuevas columnas directamente (sin JOINs) para búsquedas 10-50x más rápidas
    con aislamiento automático por workspace y compartición con teams.
    """
    name: str = "memory_search_optimized"
    description: str = (
        "🔍 BÚSQUEDA INTELIGENTE EN MEMORIA Y DOCUMENTOS - Usa esta herramienta cuando el usuario: "
        "• Busque información específica: 'busca mis notas sobre X', 'encuentra documentos de Y' "
        "• Haga preguntas sobre contenido: '¿qué escribí sobre Z?', 'muéstrame info de proyecto A' "
        "• Quiera filtrar por tema/workspace: 'busca en mi workspace de trabajo', 'notas del tema X' "
        "• Necesite memorias o documentos: 'recuerda cuando hablamos de...', 'busca el PDF sobre...' "
        "\n📋 PARÁMETROS AUTOMÁTICOS: "
        "• content_type: 'user_memories' (notas/conversaciones) o 'user_documents' (archivos/PDFs) "
        "• topic: extrae del contexto (ej: 'proyecto_hydra', 'trabajo', 'personal') "
        "• category: detecta automáticamente (ej: 'technical', 'meeting', 'idea') "
        "• workspace_id: usa el workspace actual del usuario "
        "• k: número de resultados (5-10 por defecto) "
        "\n⚡ OPTIMIZADO: 10-50x más rápido con aislamiento automático por workspace."
    )
    args_schema: Type[BaseModel] = MemorySearchOptimizedInput
    account_id: str = Field(..., description="El ID de cuenta del usuario, inyectado automáticamente.")
    workspace_id: Optional[str] = Field(None, description="ID del workspace (NULL = General), inyectado automáticamente.")
    team_id: Optional[str] = Field(None, description="ID del team propietario, inyectado automáticamente.")
    telegram_id: Optional[int] = Field(None, description="ID de Telegram del usuario, inyectado automáticamente.")

    def _run(
        self,
        query: str,
        content_type: Union[str, None] = None,
        topic: Union[str, None] = None,
        category: Union[str, None] = None,
        k: Union[int, None] = 10,
        include_shared: Union[bool, None] = True,
    ) -> str:
        """
        Realiza la búsqueda optimizada en la base de datos vectorial.
        
        Returns:
            JSON string con los resultados de la búsqueda.
        """
        try:
            results = asyncio.run(search_vector_db_optimized(
                account_id=self.account_id,
                query=query,
                content_type=content_type,
                topic=topic,
                category=category,
                workspace_id=self.workspace_id,
                team_id=self.team_id,
                visibility_teams=[] if not include_shared else None,  # TODO: obtener teams del usuario
                k=k,
            ))
            
            # Formatear resultados para el LLM
            formatted_results = []
            for i, result in enumerate(results):
                # Asegurar que los UUIDs se conviertan a string
                workspace_id = result.get("workspace_id")
                team_id = result.get("team_id")

                formatted_result = {
                    "rank": i + 1,
                    "content": result["content"],
                    "similarity_score": round(result["similarity_score"], 4),
                    "topic": result.get("topic"),
                    "category": result.get("category"),
                    "workspace_id": str(workspace_id) if workspace_id else None,
                    "team_id": str(team_id) if team_id else None,
                    "metadata": result.get("metadata", {})
                }
                formatted_results.append(formatted_result)
            
            return json.dumps({
                "status": "success",
                "query": query,
                "total_results": len(formatted_results),
                "filters_applied": {
                    "content_type": content_type,
                    "topic": topic,
                    "category": category,
                    "workspace_id": self.workspace_id,
                    "team_id": self.team_id,
                    "include_shared": include_shared
                },
                "results": formatted_results
            }, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return json.dumps({
                "status": "error",
                "error": str(e),
                "query": query
            }, ensure_ascii=False)

    async def _arun(
        self,
        query: str,
        content_type: Union[str, None] = None,
        topic: Union[str, None] = None,
        category: Union[str, None] = None,
        k: Union[int, None] = 10,
        include_shared: Union[bool, None] = True,
    ) -> str:
        """Versión asíncrona de la búsqueda optimizada."""
        try:
            results = await search_vector_db_optimized(
                account_id=self.account_id,
                query=query,
                content_type=content_type,
                topic=topic,
                category=category,
                workspace_id=self.workspace_id,
                team_id=self.team_id,
                visibility_teams=[] if not include_shared else None,  # TODO: obtener teams del usuario
                k=k,
            )
            
            # Formatear resultados para el LLM
            formatted_results = []
            for i, result in enumerate(results):
                # Asegurar que los UUIDs se conviertan a string
                workspace_id = result.get("workspace_id")
                team_id = result.get("team_id")

                formatted_result = {
                    "rank": i + 1,
                    "content": result["content"],
                    "similarity_score": round(result["similarity_score"], 4),
                    "topic": result.get("topic"),
                    "category": result.get("category"),
                    "workspace_id": str(workspace_id) if workspace_id else None,
                    "team_id": str(team_id) if team_id else None,
                    "metadata": result.get("metadata", {})
                }
                formatted_results.append(formatted_result)
            
            return json.dumps({
                "status": "success",
                "query": query,
                "total_results": len(formatted_results),
                "filters_applied": {
                    "content_type": content_type,
                    "topic": topic,
                    "category": category,
                    "workspace_id": self.workspace_id,
                    "team_id": self.team_id,
                    "include_shared": include_shared
                },
                "results": formatted_results
            }, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return json.dumps({
                "status": "error",
                "error": str(e),
                "query": query
            }, ensure_ascii=False)


class MemoryContextSearchInput(BaseModel):
    """Esquema de entrada para búsqueda con MemoryContext."""
    query: str = Field(..., description="La consulta de búsqueda")
    workspace_id: Optional[str] = Field(None, description="ID del workspace actual (NULL = General)", json_schema_extra={"type": "string"})
    team_id: Optional[str] = Field(None, description="ID del team actual", json_schema_extra={"type": "string"})
    search_type: str = Field("all", description="Tipo de búsqueda: 'memories', 'documents', 'all'")
    topic: Optional[str] = Field(None, description="Topic organizacional específico", json_schema_extra={"type": "string"})
    category: Optional[str] = Field(None, description="Categoría automática específica", json_schema_extra={"type": "string"})
    k: Optional[int] = Field(10, description="Número máximo de resultados", json_schema_extra={"type": "integer"})
    include_shared: Optional[bool] = Field(True, description="Si incluir contenido compartido", json_schema_extra={"type": "boolean"})

class MemoryContextSearchTool(BaseTool):
    """
    Herramienta que utiliza MemoryContext para búsquedas con aislamiento automático.

    Proporciona una interfaz simplificada que maneja automáticamente el contexto
    del usuario (workspace, teams, permisos) para búsquedas aisladas.
    """
    name: str = "memory_context_search"
    description: str = (
        "Realiza búsquedas con aislamiento automático usando MemoryContext. "
        "Maneja automáticamente el contexto del usuario (workspace, teams, permisos). "
        "Soporta búsqueda en memorias, documentos o ambos con filtrado por topic/category. "
        "Ideal para búsquedas contextuales que respetan el aislamiento por workspace."
    )
    args_schema: Type[BaseModel] = MemoryContextSearchInput

    account_id: str = Field(..., description="El ID de cuenta del usuario, inyectado automáticamente.")

    def _run(
        self,
        query: str,
        workspace_id: Union[str, None] = None,
        team_id: Union[str, None] = None,
        search_type: str = "all",
        topic: Union[str, None] = None,
        category: Union[str, None] = None,
        k: Union[int, None] = 10,
        include_shared: Union[bool, None] = True,
    ) -> str:
        """Realiza búsqueda con MemoryContext."""
        return asyncio.run(self._arun(
            query, workspace_id, team_id, search_type,
            topic, category, k, include_shared
        ))

    async def _arun(
        self,
        query: str,
        workspace_id: Union[str, None] = None,
        team_id: Union[str, None] = None,
        search_type: str = "all",
        topic: Union[str, None] = None,
        category: Union[str, None] = None,
        k: Union[int, None] = 10,
        include_shared: Union[bool, None] = True,
    ) -> str:
        """Versión asíncrona de búsqueda con MemoryContext."""
        try:
            context = await create_memory_context(
                account_id=self.account_id,
                workspace_id=workspace_id,
                team_id=team_id
            )
            
            # Realizar búsqueda según el tipo
            if search_type == "memories":
                results = await context.search_memories(query, topic, category, k if k is not None else 10, include_shared if include_shared is not None else True)
                return json.dumps({
                    "status": "success",
                    "search_type": "memories",
                    "workspace": workspace_id or "General",
                    "results": results
                }, ensure_ascii=False, indent=2)
                
            elif search_type == "documents":
                results = await context.search_documents(query, topic, category, k if k is not None else 10, include_shared if include_shared is not None else True)
                return json.dumps({
                    "status": "success",
                    "search_type": "documents", 
                    "workspace": workspace_id or "General",
                    "results": results
                }, ensure_ascii=False, indent=2)
                
            else:  # search_type == "all"
                results = await context.search_all(query, topic, category, k if k is not None else 10, include_shared if include_shared is not None else True)
                return json.dumps({
                    "status": "success",
                    "search_type": "all",
                    "workspace": workspace_id or "General",
                    "memories_count": len(results["memories"]),
                    "documents_count": len(results["documents"]),
                    "results": results
                }, ensure_ascii=False, indent=2)
                
        except Exception as e:
            return json.dumps({
                "status": "error",
                "error": str(e),
                "query": query
            }, ensure_ascii=False)
