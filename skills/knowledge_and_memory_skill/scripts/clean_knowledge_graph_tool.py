# skills/knowledge_and_memory_skill/scripts/clean_knowledge_graph_tool.py

import logging
from typing import Any, Optional, Type

from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

from core.database import get_graph_db
from core.llm_manager import get_main_llm
from knowledge_graph.entity_quality_reviewer import EntityQualityReviewer

logger = logging.getLogger(__name__)

class CleanKnowledgeGraphInput(BaseModel):
    """
    Define el esquema de entrada para la herramienta de limpieza del grafo.
    """
    workspace_id: Optional[str] = Field(
        None,
        description="ID del workspace a limpiar. Si no se especifica, se limpia todo el grafo."
    )

class CleanKnowledgeGraphTool(BaseTool):
    """
    Herramienta para limpiar y optimizar el grafo de conocimiento.
    """
    name: str = "clean_knowledge_graph_tool"
    description: str = (
        "Herramienta que revisa y limpia el grafo de conocimiento del usuario. "
        "Detecta entidades duplicadas, elimina información irrelevante o genérica y "
        "organiza el grafo unificando conceptos similares. Úsala cuando el usuario "
        "pida 'limpiar memoria', 'ordenar grafo', 'eliminar duplicados', etc."
    )
    args_schema: Type[BaseModel] = CleanKnowledgeGraphInput
    return_direct: bool = False
    
    account_id: str = Field(..., description="El identificador de la cuenta, inyectado automáticamente.")
    workspace_id: Optional[str] = Field(None, description="El identificador del workspace, inyectado automáticamente.")

    async def _arun(self, workspace_id: Optional[str] = None, run_manager: Optional[Any] = None, **kwargs: Any) -> str:
        if not self.account_id:
            return "Error: No se pudo obtener el account_id. Esta herramienta requiere identificación del usuario."

        target_workspace = workspace_id or self.workspace_id

        logger.info(f"Iniciando limpieza de grafo para la cuenta '{self.account_id}', workspace: '{target_workspace}'")

        try:
            db = get_graph_db()
            llm = get_main_llm()
            
            reviewer = EntityQualityReviewer(graph_db=db, llm=llm)
            
            review_results = await reviewer.review_all_entities(workspace_id=target_workspace)
            corrections = review_results.get('corrections', [])
            
            if not corrections:
                return "El grafo de conocimiento ha sido analizado y ya se encuentra óptimo. No se encontraron duplicados ni problemas."
                
            apply_results = await reviewer.apply_corrections(corrections, auto_apply=True)
            
            return (f"Limpieza de grafo completada exitosamente. "
                    f"Se encontraron {len(correcciones)} problemas (como duplicados o irrelevancias). "
                    f"Se aplicaron {apply_results.get('applied', 0)} correcciones automáticas.")
            
        except Exception as e:
            logger.error(f"Error en CleanKnowledgeGraphTool para la cuenta '{self.account_id}': {e}", exc_info=True)
            return f"Ocurrió un error al intentar limpiar el grafo de conocimiento: {e}"

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("CleanKnowledgeGraphTool no soporta ejecución síncrona.")
