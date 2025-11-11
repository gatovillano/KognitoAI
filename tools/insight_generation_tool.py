# tools/insight_generation_tool.py

import logging
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

from core.database import SessionLocal, Nota, LangchainPgEmbedding
from core.notes_manager import NotesManager
from tools.analyze_text_for_insights_tool import AnalyzeTextForInsightsTool
from tools.cognee_knowledge_graph_tool import CogneeKnowledgeGraphTool
from knowledge_graph.cognee_integration import CogneeIntegration
from knowledge_graph.graph_database import GraphDB
from core.config import settings

logger = logging.getLogger(__name__)

class InsightGenerationInput(BaseModel):
    """Define el esquema de entrada para la Herramienta de Generación de Insights y Propuestas."""
    query: str = Field(
        ...,
        description="La consulta o el tema principal sobre el que el usuario desea generar ideas, propuestas o insights."
    )
    account_id: str = Field(
        ...,
        description="El ID de cuenta del usuario, inyectado automáticamente."
    )
    workspace_id: Optional[str] = Field(
        None,
        description="El ID del espacio de trabajo del usuario, inyectado automáticamente si aplica."
    )
    # Parámetros opcionales para refinar la búsqueda o el análisis
    search_category: Optional[str] = Field(
        None,
        description="Categoría opcional para filtrar las notas y documentos relevantes."
    )
    max_notes_to_retrieve: int = Field(
        10,
        description="Número máximo de notas o documentos a recuperar para el análisis."
    )
    focus_area: Optional[str] = Field(
        None,
        description="Un área específica de enfoque para guiar la generación de insights."
    )

class InsightGenerationTool(BaseTool):
    """
    Herramienta integral para generar ideas, propuestas e insights a partir de las notas
    y la base de conocimiento del usuario, utilizando RAG y el grafo de conocimiento.
    """
    name: str = "insight_generation_tool"
    description: str = (
        "Útil para generar ideas, propuestas o insights innovadores sobre un tema o consulta específica. "
        "Combina la recuperación de información (RAG) de las notas y documentos del usuario con un análisis "
        "profundo de texto y el poder del grafo de conocimiento para descubrir patrones y conexiones ocultas. "
        "Puede filtrar por categoría y enfocar el análisis en un área particular."
    )
    args_schema: Type[BaseModel] = InsightGenerationInput
    return_direct: bool = False

    # Dependencias inyectadas (se inicializarán en el constructor o en _arun si no están presentes)
    _cognee_kg_tool: Optional[CogneeKnowledgeGraphTool] = None
    _analyze_text_tool: Optional[AnalyzeTextForInsightsTool] = None

    def __init__(self, **data: Any):
        super().__init__(**data)
        # Inicializar herramientas dependientes si no se inyectan
        if self._cognee_kg_tool is None:
            # Asegurarse de que GraphDB y CogneeIntegration estén inicializados
            graph_db = GraphDB(
                uri=settings.neo4j_uri,
                user=settings.neo4j_user,
                password=settings.neo4j_password
            )
            graph_db.connect()
            cognee_integration = CogneeIntegration(graph_db)
            self._cognee_kg_tool = CogneeKnowledgeGraphTool(
                cognee_integration=cognee_integration,
                graph_db=graph_db,
                account_id=self.account_id,
                workspace_id=self.workspace_id
            )
        if self._analyze_text_tool is None:
            self._analyze_text_tool = AnalyzeTextForInsightsTool(
                account_id=self.account_id,
                workspace_id=self.workspace_id
            )

    async def _arun(
        self,
        query: str,
        account_id: str,
        workspace_id: Optional[str] = None,
        search_category: Optional[str] = None,
        max_notes_to_retrieve: int = 10,
        focus_area: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        logger.info(f"Iniciando InsightGenerationTool para cuenta {account_id}, query: '{query}'")

        # 1. Recuperación de Contexto (RAG Semántico)
        retrieved_texts = await self._retrieve_relevant_content(
            account_id,
            query,
            workspace_id,
            search_category,
            max_notes_to_retrieve
        )

        if not retrieved_texts:
            return "No se encontró información relevante en tus notas o base de conocimiento para generar insights."

        combined_content = "\n\n".join([text for text in retrieved_texts])
        logger.info(f"Contenido combinado para análisis (primeros 200 chars): {combined_content[:200]}...")

        # 2. Análisis Preliminar de Texto
        preliminary_analysis_result = await self._analyze_text_tool._arun(text=combined_content)
        logger.info(f"Análisis preliminar de texto completado: {preliminary_analysis_result}")

        # Extraer temas clave y brechas de conocimiento del análisis preliminar
        # Esto requerirá un parseo más sofisticado si preliminary_analysis_result es un string formateado
        # Por ahora, asumiremos que podemos extraer esto o que el LLM lo hará.

        # 3. Generación Avanzada de Insights y Propuestas con el Grafo de Conocimiento
        # Usaremos el CogneeKnowledgeGraphTool para esto

        # Preparar la query para el grafo
        kg_query = f"Genera ideas y propuestas innovadoras basadas en '{query}'. Considera los siguientes textos: {combined_content}"
        if focus_area:
            kg_query += f" Con un enfoque especial en: {focus_area}."
        
        # Intentar extraer directamente insights del grafo
        insights_from_kg = await self._cognee_kg_tool._arun(
            action="get_insights",
            query=kg_query,
            dataset_name=f"user_{account_id.replace('-', '_')}", # Usar un dataset específico del usuario
            return_type="summary", # Queremos un resumen de insights
            account_id=account_id,
            workspace_id=workspace_id
        )
        logger.info(f"Insights del grafo de conocimiento: {insights_from_kg}")

        # Combinar resultados y formatear la respuesta final
        final_response = self._format_final_insights(
            query,
            retrieved_texts,
            preliminary_analysis_result,
            insights_from_kg
        )
        
        return final_response

    def _run(self, *args: Any, **kwargs: Any) -> str:
        """Ejecuta la herramienta de forma síncrona (no recomendada)."""
        raise NotImplementedError("InsightGenerationTool no soporta ejecución síncrona.")

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
        async with SessionLocal() as session:
            notes_manager = NotesManager(session)
            
            # Buscar en notas
            total_notes, notes_data = await notes_manager.get_notes_as_dicts(
                account_id=account_id,
                search_query=query,
                workspace_id=workspace_id,
                category=category,
                limit=limit
            )
            note_contents = [note["content"] for note in notes_data]

            # Buscar directamente en LangchainPgEmbedding si es necesario,
            # aunque NotesManager ya debería cubrir las notas.
            # Aquí podríamos añadir lógica para buscar otros tipos de documentos
            # que no sean notas pero estén en langchain_pg_embedding.
            # Por ahora, nos basaremos principalmente en NotesManager para la parte de notas.
            
            # Esto es un placeholder; la búsqueda en LangchainPgEmbedding para documentos
            # generales necesitaría su propia lógica o una herramienta dedicada.
            # Por ahora, asumimos que NotesManager es nuestra fuente principal de RAG.
            
            # Si necesitamos buscar otros tipos de documentos en langchain_pg_embedding
            # que no sean notas, tendríamos que implementar una consulta SQL directa aquí
            # o usar una herramienta como vector_db_search_tool si existiera.
            
            # Ejemplo de cómo se podría buscar en LangchainPgEmbedding para 'document_chunk'
            # if not note_contents: # Solo si no encontramos notas, buscar en documentos generales
            #     stmt = select(LangchainPgEmbedding.document).where(
            #         LangchainPgEmbedding.account_id == uuid.UUID(account_id),
            #         LangchainPgEmbedding.content_type == 'document_chunk',
            #         LangchainPgEmbedding.document.ilike(f"%{query}%") # Búsqueda simple por texto
            #     ).limit(limit)
            #     result = await session.execute(stmt)
            #     document_chunks = [row.document for row in result.scalars().all()]
            #     return document_chunks
            
            return note_contents

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
