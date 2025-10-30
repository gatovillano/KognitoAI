import json
import logging
from typing import Any, Dict, List, Literal, Optional, Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from core.database import Account as User
from utils.security import get_current_user
from knowledge_graph.cognee_integration import CogneeIntegration
from knowledge_graph.graph_database import GraphDB
from core.config import settings
from api.knowledge_graph import get_cognee_integration


logger = logging.getLogger(__name__)
router = APIRouter()

# --- Modelo de Entrada para el Endpoint ---
class GraphVisualizationRequest(BaseModel):
    dataset_name: str = Field(..., description="El nombre del dataset a visualizar.")
    focus_query: Optional[str] = Field(None, description="Una consulta en lenguaje natural para enfocar la visualización en un subgrafo específico.")
    max_nodes: Optional[int] = Field(50, description="Número máximo de nodos a devolver.")
    max_hops: Optional[int] = Field(1, description="Número máximo de saltos a explorar desde los nodos de la consulta.")

# --- Endpoint POST para obtener datos de visualización ---
@router.post("/graph/visualize", response_model=Dict[str, Any])
async def get_graph_visualization_data_endpoint(
    request_data: GraphVisualizationRequest,
    current_user: Annotated[User, Depends(get_current_user)], # Autenticación/Autorización
    cognee_integration: CogneeIntegration = Depends(get_cognee_integration) # Inyectar la instancia de CogneeIntegration
):
    logger.info(f"Received request for graph visualization: {request_data.model_dump_json()}")
    try:
        # El dataset_name en el backend ya incluye el account_id para aislamiento.
        # Usamos el dataset_name proporcionado en la solicitud para asegurar que coincida con el workspace.
        dataset_name_to_use = request_data.dataset_name

        # Llamar al método de CogneeIntegration para obtener los datos del grafo
        graph_data = await cognee_integration.get_visualization_data(
            dataset_name=dataset_name_to_use,
            focus_query=request_data.focus_query,
            max_nodes=request_data.max_nodes if request_data.max_nodes is not None else 50,
            max_hops=request_data.max_hops if request_data.max_hops is not None else 1
        )
        
        return {
            "status": "success",
            "message": "Datos de visualización del grafo obtenidos con éxito.",
            "dataset_name": request_data.dataset_name,
            "focus_query": request_data.focus_query,
            "nodes": graph_data.get("nodes", []),
            "edges": graph_data.get("edges", []),
            "summary": graph_data.get("summary", "")
        }

    except HTTPException as e:
        logger.error(f"Error HTTP en endpoint de visualización de grafo: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"Error inesperado al obtener datos de visualización del grafo: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor al procesar la solicitud de visualización del grafo: {e}"
        )