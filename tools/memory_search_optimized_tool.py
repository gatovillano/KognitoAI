from typing import Union, Type, Optional, Any
from pydantic import BaseModel, Field
import asyncio
import json
from core.memory_manager import create_memory_context, search_vector_db_optimized
from langchain_core.tools import BaseTool

class MemorySearchOptimizedInput(BaseModel):
    """Esquema de entrada para la herramienta de búsqueda optimizada de memoria."""
    query: str = Field(..., description="Consulta de búsqueda", json_schema_extra={"type": "string"})
    content_type: Optional[str] = Field(None, description="Tipo de contenido", json_schema_extra={"type": "string"})
    topic: Optional[str] = Field(None, description="Tema específico", json_schema_extra={"type": "string"})
    category: Optional[str] = Field(None, description="Categoría", json_schema_extra={"type": "string"})
    workspace_id: Optional[str] = Field(None, description="ID del workspace", json_schema_extra={"type": "string"})
    k: int = Field(10, description="Número de resultados", json_schema_extra={"type": "integer"})

class MemorySearchOptimizedTool(BaseTool):
    """Herramienta optimizada para búsqueda de memoria."""
    name: str = "memory_search_optimized"
    description: str = "Búsqueda optimizada en la memoria del usuario"
    args_schema: Type[BaseModel] = MemorySearchOptimizedInput

    account_id: str = Field(default="", description="ID de la cuenta asociada a esta herramienta.")

    def __init__(self, account_id: str = "", **kwargs):
        super().__init__(**kwargs)
        self.account_id = account_id

    def _run(
        self,
        tool_input: str,
        run_manager: Optional[Any] = None,
        **kwargs: Any
    ) -> str:
        """Versión síncrona que llama a la versión asíncrona."""
        return asyncio.run(self._arun(tool_input, run_manager, **kwargs))

    async def _arun(
        self,
        tool_input: str,
        run_manager: Optional[Any] = None,
        **kwargs: Any
    ) -> str:
        """Versión asíncrona de la búsqueda optimizada."""
                # Obtener account_id del contexto de configuración o instancia
        account_id = None
        if run_manager and hasattr(run_manager, 'config'):
            config = getattr(run_manager, 'config', {})
            configurable = config.get('configurable', {})
            account_id = configurable.get('account_id')
        if not account_id:
            account_id = getattr(self, 'account_id', "")

        # Validar que tenemos account_id
        if not account_id:
            return "Error: No se pudo obtener el account_id. Esta herramienta requiere identificación del usuario."

        try:
            # Parse tool_input if it's a JSON string, otherwise treat as query
            if isinstance(tool_input, str) and tool_input.startswith('{'):
                import json as json_module
                input_data = json_module.loads(tool_input)
                query = input_data.get("query", tool_input)
                content_type = input_data.get("content_type")
                topic = input_data.get("topic")
                category = input_data.get("category")
                workspace_id = input_data.get("workspace_id")
                k = input_data.get("k", 10)
            else:
                query = tool_input
                content_type = None
                topic = None
                category = None
                workspace_id = None
                k = 10

            results = await search_vector_db_optimized(
                account_id=self.account_id,
                query=query,
                content_type=content_type,
                topic=topic,
                category=category,
                workspace_id=workspace_id,
                team_id=None,  # Se puede agregar como parámetro si es necesario
                visibility_teams=None,  # Se puede agregar como parámetro si es necesario
                k=k,
            )

            # Formatear resultados para el LLM
            formatted_results = []
            for i, result in enumerate(results):
                # Asegurar que los UUIDs se conviertan a string
                result_workspace_id = result.get("workspace_id")
                result_team_id = result.get("team_id")

                formatted_result = {
                    "rank": i + 1,
                    "content": result["content"],
                    "similarity_score": round(result["similarity_score"], 4),
                    "topic": result.get("topic"),
                    "category": result.get("category"),
                    "workspace_id": str(result_workspace_id) if result_workspace_id else None,
                    "team_id": str(result_team_id) if result_team_id else None,
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
                    "workspace_id": workspace_id,
                    "team_id": None,
                    "include_shared": None
                },
                "results": formatted_results
            }, ensure_ascii=False, indent=2)

        except Exception as e:
            return json.dumps({
                "status": "error",
                "error": str(e),
                "query": tool_input
            }, ensure_ascii=False)

class MemoryContextSearchInput(BaseModel):
    """Esquema de entrada para búsqueda con MemoryContext."""
    account_id: str = Field(..., description="ID de la cuenta", json_schema_extra={"type": "string"})
    query: str = Field(..., description="Consulta de búsqueda", json_schema_extra={"type": "string"})
    workspace_id: Optional[str] = Field(None, description="ID del workspace", json_schema_extra={"type": "string"})
    team_id: Optional[str] = Field(None, description="ID del equipo", json_schema_extra={"type": "string"})
    search_type: str = Field("all", description="Tipo de búsqueda: 'memories', 'documents', o 'all'", json_schema_extra={"type": "string"})
    topic: Optional[str] = Field(None, description="Tema específico", json_schema_extra={"type": "string"})
    category: Optional[str] = Field(None, description="Categoría", json_schema_extra={"type": "string"})
    k: int = Field(10, description="Número de resultados", json_schema_extra={"type": "integer"})
    include_shared: bool = Field(True, description="Incluir contenido compartido", json_schema_extra={"type": "boolean"})

class MemoryContextSearchTool(BaseTool):
    """Herramienta para búsqueda con MemoryContext."""
    name: str = "memory_context_search"
    description: str = "Búsqueda avanzada usando MemoryContext"
    args_schema: Type[BaseModel] = MemoryContextSearchInput

    def _run(
        self,
        tool_input: str,
        run_manager: Optional[Any] = None,
        **kwargs: Any
    ) -> str:
        """Realiza búsqueda con MemoryContext."""
        return asyncio.run(self._arun(tool_input, run_manager, **kwargs))

    async def _arun(
        self,
        tool_input: str,
        run_manager: Optional[Any] = None,
        **kwargs: Any
    ) -> str:
        """Versión asíncrona de búsqueda con MemoryContext."""
                # Obtener account_id del contexto de configuración o instancia
        account_id = None
        if run_manager and hasattr(run_manager, 'config'):
            config = getattr(run_manager, 'config', {})
            configurable = config.get('configurable', {})
            account_id = configurable.get('account_id')
        if not account_id:
            account_id = getattr(self, 'account_id', "")

        # Validar que tenemos account_id
        if not account_id:
            return "Error: No se pudo obtener el account_id. Esta herramienta requiere identificación del usuario."

        try:
            # Parse tool_input if it's a JSON string, otherwise treat as query
            if isinstance(tool_input, str) and tool_input.startswith('{'):
                import json as json_module
                input_data = json_module.loads(tool_input)
                account_id = input_data.get("account_id", "")
                query = input_data.get("query", tool_input)
                workspace_id = input_data.get("workspace_id")
                team_id = input_data.get("team_id")
                search_type = input_data.get("search_type", "all")
                topic = input_data.get("topic")
                category = input_data.get("category")
                k = input_data.get("k", 10)
                include_shared = input_data.get("include_shared", True)
            else:
                # Default values if tool_input is just a query string
                account_id = ""
                query = tool_input
                workspace_id = None
                team_id = None
                search_type = "all"
                topic = None
                category = None
                k = 10
                include_shared = True

            # Crear contexto de memoria
            context = await create_memory_context(
                account_id=account_id,
                workspace_id=workspace_id,
                team_id=team_id
            )

            # Realizar búsqueda según el tipo
            if search_type == "memories":
                results = await context.search_memories(
                    query, topic, category,
                    k if k is not None else 10,
                    include_shared if include_shared is not None else True
                )
                return json.dumps({
                    "status": "success",
                    "search_type": "memories",
                    "workspace": workspace_id or "General",
                    "results": results
                }, ensure_ascii=False, indent=2)

            elif search_type == "documents":
                results = await context.search_documents(
                    query, topic, category,
                    k if k is not None else 10,
                    include_shared if include_shared is not None else True
                )
                return json.dumps({
                    "status": "success",
                    "search_type": "documents",
                    "workspace": workspace_id or "General",
                    "results": results
                }, ensure_ascii=False, indent=2)

            else:  # search_type == "all"
                results = await context.search_all(
                    query, topic, category,
                    k if k is not None else 10,
                    include_shared if include_shared is not None else True
                )
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
                "query": tool_input
            }, ensure_ascii=False)
