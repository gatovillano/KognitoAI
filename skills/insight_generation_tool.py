# tools/insight_generation_tool.py

import logging
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

from core.database import SessionLocal, Nota, LangchainPgEmbedding
from core.notes_manager import NotesManager
from tools.analyze_text_for_insights_tool import AnalyzeTextForInsightsTool
from tools.knowledge_graph_tool import KnowledgeGraphTool
from knowledge_graph.graph_integration import GraphIntegration
from knowledge_graph.graph_database import GraphDB
from core.config import settings

from utils.db_session import DBSession

logger = logging.getLogger(__name__)

class InsightGenerationInput(BaseModel):
    query: str = Field(..., description="La consulta o tema sobre el cual generar insights.")
    account_id: str = Field(..., description="El ID de la cuenta del usuario.")
    workspace_id: Optional[str] = Field(None, description="El ID del workspace (opcional).")
    category: Optional[str] = Field(None, description="Categoría de notas a filtrar (opcional).")
    limit: int = Field(5, description="Número máximo de notas/documentos a recuperar.")

class InsightGenerationTool(BaseTool):
    name: str = "insight_generation_tool"
    description: str = "Genera insights profundos combinando análisis de texto de notas y conexiones del grafo de conocimiento."
    args_schema: Type[BaseModel] = InsightGenerationInput
    account_id: Optional[str] = Field(None, description="ID de la cuenta inyectado automáticamente")

    async def _arun(
        self,
        query: str,
        account_id: str,
        workspace_id: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 5
    ) -> str:
        """
        Ejecuta la generación de insights.
        """
        try:
            # 1. Recuperar contenido relevante
            retrieved_texts = await self._retrieve_relevant_content(account_id, query, workspace_id, category, limit)
            
            if not retrieved_texts:
                return f"No se encontró contenido relevante para '{query}' en tus notas o documentos."

            combined_text = "\n\n".join(retrieved_texts)

            # 2. Análisis preliminar de texto (usando AnalyzeTextForInsightsTool)
            analyzer_tool = AnalyzeTextForInsightsTool()
            preliminary_analysis = await analyzer_tool._arun(combined_text, query)

            # 3. Consultar el Grafo de Conocimiento (usando KnowledgeGraphTool o integración directa)
            # Usamos la integración directa para más control o la herramienta si es suficiente.
            # Aquí usaremos la herramienta para mantener la consistencia.
            kg_tool = KnowledgeGraphTool(account_id=account_id)
            kg_insights = await kg_tool._arun(
                action="get_insights",
                query=query,
                dataset_name=f"kognito_{account_id}"
            )

            # 4. Formatear la respuesta final
            final_response = self._format_final_insights(query, retrieved_texts, preliminary_analysis, kg_insights)
            
            return final_response

        except Exception as e:
            logger.error(f"Error generando insights para '{query}': {e}", exc_info=True)
            return f"Ocurrió un error al generar insights: {e}"

    async def _retrieve_relevant_content(
        self,
        account_id: str,
        query: str,
        workspace_id: Optional[str],
        category: Optional[str],
        limit: int
    ) -> List[str]:
        """
        Recupera el contenido más relevante de notas y embeddings de documentos
        utilizando el NotesManager y la tabla LangchainPgEmbedding.
        """
        async with DBSession(SessionLocal) as session:
            notes_manager = NotesManager(session)

            # 1️⃣ Buscar en notas
            total_notes, notes_data = await notes_manager.get_notes_as_dicts(
                account_id=account_id,
                search_query=query,
                workspace_id=workspace_id,
                category=category,
                limit=limit,
            )
            note_contents = [note["content"] for note in notes_data]

            # 2️⃣ Buscar en embeddings de documentos (LangchainPgEmbedding)
            #    Realizamos una búsqueda simple por coincidencia de texto en el campo `document`
            #    y en el título almacenado en `cmetadata->>'title'`.
            embedding_query = """
                SELECT document
                FROM langchain_pg_embedding
                WHERE account_id = :account_id
                  AND (document ILIKE :search_pattern
                       OR cmetadata->>'title' ILIKE :search_pattern)
                LIMIT :limit
            """
            params = {
                "account_id": account_id,
                "search_pattern": f"%{query}%",
                "limit": limit,
            }
            result = await session.execute(embedding_query, params)
            embedding_contents = [row[0] for row in result.fetchall()]

            # 3️⃣ Combinar resultados (notas + documentos)
            combined_contents = note_contents + embedding_contents
            return combined_contents

    def _format_final_insights(
        self,
        query: str,
        retrieved_texts: List[str],
        preliminary_analysis_result: str,
        insights_from_kg: str
    ) -> str:
        """
        Formatea los resultados combinados de los insights para el usuario.
        """
        formatted_response = f"## 💡 Insights y Propuestas Generadas para: '{query}'\n\n"
        formatted_response += "### 🔍 Análisis Preliminar del Contenido Relevante:\n"
        formatted_response += f"{preliminary_analysis_result}\n\n"
        formatted_response += "### 🧠 Conexiones y Ideas del Grafo de Conocimiento:\n"
        formatted_response += f"{insights_from_kg}\n\n"
        formatted_response += "### 📚 Contenido de Referencia Clave:\n"
        for i, text in enumerate(retrieved_texts, 1):
            formatted_response += f"**Fragmento {i}:**\n{text[:250]}...\n\n" # Mostrar un fragmento
        
        formatted_response += (
            "---"
            "\n\nEsta es una generación inicial de ideas. Te animo a explorar las 'Brechas de Conocimiento' "
            "identificadas en el análisis preliminar y las 'Conexiones y Ideas del Grafo' para profundizar "
            "y desarrollar aún más tus propias propuestas. ¡Tu conocimiento es la clave! 🚀"
        )
        return formatted_response

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("insight_generation_tool no soporta ejecución síncrona.")
