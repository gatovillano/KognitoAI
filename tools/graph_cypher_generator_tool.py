import logging
import json
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Type

from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from langchain_core.language_models import BaseLanguageModel # Importar el tipo base del LLM

# Importar tu gestor de LLMs
from core.llm_manager import get_fast_llm
# Importar tu integración con Cognee/Neo4j
from knowledge_graph.graph_integration import GraphIntegration

logger = logging.getLogger(__name__)

# --- Modelo de Entrada para la Herramienta ---
class GraphCypherGeneratorToolInput(BaseModel):
    natural_language_query: str = Field(..., description="La pregunta o descripción completa en lenguaje natural sobre lo que se desea encontrar o analizar en el grafo de conocimiento.")
    dataset_name: str = Field(..., description="El nombre del dataset (colección de conocimiento) específico donde se debe realizar la búsqueda.")
    return_type: Optional[Literal["nodes", "relationships", "paths", "summary", "cypher_query_only", "stats"]] = Field(
        "summary",
        description="El formato deseado para los resultados: 'nodes', 'relationships', 'paths', 'summary', 'cypher_query_only', 'stats'."
    )

# --- Definición de la Herramienta ---
class GraphCypherGeneratorTool(BaseTool):
    name: str = "graph_cypher_generator_tool"
    description: str = "Generador Inteligente de Consultas Cypher para Grafos de Conocimiento. Traduce tu pregunta en lenguaje natural a una consulta Cypher optimizada, la ejecuta y devuelve los resultados."
    args_schema: Type[BaseModel] = GraphCypherGeneratorToolInput

    account_id: Optional[str] = None # Se inyecta después de la instanciación
    _cognee_integration: Optional[GraphIntegration] = None
    _fast_llm: Optional[BaseLanguageModel] = None # Tipo para el LLM rápido

    def _get_graph_integration(self) -> GraphIntegration:
        if self._cognee_integration is None:
            # This assumes GraphIntegration can be initialized without arguments.
            # If it needs the graph_db, this will need to be refactored.
            from knowledge_graph.graph_database import GraphDB
            graph_db = GraphDB()
            self._cognee_integration = GraphIntegration(graph_db=graph_db)
        return self._cognee_integration

    def _get_fast_llm_instance(self) -> BaseLanguageModel: # Renombrado para evitar conflicto con la función global
        if self._fast_llm is None:
            self._fast_llm = get_fast_llm()
            if not self._fast_llm:
                raise ValueError("Fast LLM no está inicializado. Asegúrate de que initialize_llms() se ha ejecutado.")
        return self._fast_llm

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("GraphCypherGeneratorTool no soporta ejecución síncrona.")

    async def _arun(
        self,
        natural_language_query: str,
        dataset_name: str,
        return_type: Literal["nodes", "relationships", "paths", "summary", "cypher_query_only", "stats"] = "summary",
        run_manager: Optional[Any] = None,
        **kwargs
    ) -> str:
        graph_integration = self._get_graph_integration()
        fast_llm = self._get_fast_llm_instance() # Usar el método de la clase
        dataset_name_with_account = f"{dataset_name}_{self.account_id.replace('-', '_')}"

        try:
            # --- PASO 1: Generación de la Consulta Cypher por el FAST LLM ---
            logger.info(f"⚡ Generando Cypher para: '{natural_language_query}' en dataset: {dataset_name_with_account} usando Fast LLM.")
            
            # El prompt es crucial para la precisión del FAST LLM
            cypher_generation_prompt = f"""
            Eres un experto en el lenguaje de consulta Cypher y en la estructura de grafos de conocimiento.
            Tu tarea es traducir la siguiente pregunta en lenguaje natural a una consulta Cypher optimizada para Neo4j.
            El grafo contiene nodos de tipo 'CONCEPTUAL_QUOTE' y relaciones de varios tipos.
            Todos los nodos y relaciones tienen una propiedad 'dataset_name'.
            Los nodos 'CONCEPTUAL_QUOTE' tienen propiedades como 'name', 'description', 'category', 'concept', 'full_text'.
            Las relaciones tienen propiedades como 'type' y 'description', 'full_text'.

            **Reglas estrictas para la generación de Cypher:**
            1.  **Siempre filtra por el dataset:** Incluye `n.dataset_name = '{dataset_name_with_account}'` para nodos y `r.dataset_name = '{dataset_name_with_account}'` para relaciones.
            2.  **Usa `name` o `concept` para buscar conceptos:** Para identificar nodos específicos, usa `n.name` o `n.concept`.
            3.  **Usa `CONTAINS` para búsquedas parciales de texto:** Si la pregunta implica "sobre" o "contiene", usa `CONTAINS` (ej. `n.description CONTAINS 'palabra'`).
            4.  **Para encontrar caminos:** Usa `MATCH path = (s)-[*1..X]-(t) RETURN path`. Si la pregunta pide el "camino más corto", usa `shortestPath`.
            5.  **Para estadísticas o conteos:** Usa funciones de agregación como `COUNT()`, `SUM()`.
            6.  **Para relaciones directas:** `(n)-[r]->(m)`.
            7.  **Para cualquier tipo de relación:** `(n)-[r]->(m)` sin especificar el tipo `r`.
            8.  **Para tipos de relación específicos:** `(n)-[:TIPO_RELACION]->(m)`.
            9.  **Devuelve los elementos relevantes:** Si se pide una lista de nodos, devuelve `n`. Si se piden relaciones, devuelve `r`. Si se piden caminos, devuelve `path`. Si se piden nodos y relaciones, devuelve `n, r, m`.
            10. **Asegúrate de que la consulta sea válida y ejecutable en Neo4j.**
            11. **Devuelve SOLO la consulta Cypher, sin explicaciones, formato Markdown, ni texto adicional.**

            Pregunta en lenguaje natural: "{natural_language_query}"
            Consulta Cypher:
            """
            
            # Usar el método .invoke para obtener la respuesta del LLM
            generated_cypher_query = fast_llm.invoke(cypher_generation_prompt).content.strip()

            logger.info(f"Generated Cypher by FAST LLM: {generated_cypher_query}")

            # --- PASO 2: Validación y Ejecución de la Consulta Cypher ---
            # Validación básica de la sintaxis Cypher
            if not generated_cypher_query.lower().startswith(("match", "call", "return")):
                logger.error(f"Cypher generado inválido: {generated_cypher_query}")
                raise ValueError("La consulta Cypher generada parece inválida o no empieza con MATCH/CALL/RETURN.")
            
            # Aquí podrías añadir una validación más robusta si fuera necesario,
            # por ejemplo, usando un parser Cypher si tuvieras uno.

            if return_type == "cypher_query_only":
                return f"Consulta Cypher generada:\n```cypher\n{generated_cypher_query}\n```"

            # Ejecutar la consulta en Neo4j
            raw_results = await graph_integration.graph_db.execute_query(generated_cypher_query)

            # --- PASO 3: Formateo de Resultados ---
            formatted_results = graph_integration._format_advanced_search_results(raw_results, return_type)


            if not formatted_results and return_type != "summary":
                return f"No se encontraron resultados en el grafo para la consulta: '{natural_language_query}'."

            # Generar un resumen si el return_type es "summary" o si no hay resultados detallados
            summary_output = ""
            if return_type == "summary" or not formatted_results:
                summary_prompt = f"""
                Eres un experto en resumir información de grafos de conocimiento.
                Resume la siguiente información extraída del grafo de conocimiento en lenguaje natural, de forma concisa y clara.
                Si no hay resultados, indica que no se encontró información relevante.

                Información del grafo: {formatted_results if formatted_results else 'No se encontraron resultados detallados.'}

                Resumen:
                """
                summary_output = fast_llm.invoke(summary_prompt).content.strip()
            
            # Construir la respuesta final de la herramienta
            response_payload = {
                "query": natural_language_query,
                "dataset_name": dataset_name,
                "status": "query_completed",
                "method": "cypher_llm_generated",
                "searched_at": datetime.now().isoformat()
            }

            if return_type == "summary" or not formatted_results:
                response_payload["results_summary"] = summary_output
            else:
                response_payload["results"] = formatted_results
            
            return json.dumps(response_payload, ensure_ascii=False, indent=2) # Devolver JSON

        except ValueError as ve:
            logger.error(f"Error de validación de Cypher o del LLM: {ve}", exc_info=True)
            return f"Error al generar o validar la consulta Cypher: {ve}. Por favor, reformula tu pregunta. (Detalle técnico: {ve})"
        except Exception as e:
            logger.error(f"Error al ejecutar la consulta Cypher generada para '{natural_language_query}': {e}", exc_info=True)
            return f"Lo siento, hubo un error al consultar el grafo. Por favor, intenta de nuevo o reformula tu pregunta. (Detalle técnico: {e})"