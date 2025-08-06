# utils/multi_query_retriever.py

"""
MultiQueryRetriever para Kognito AI
Genera múltiples consultas reformuladas para mejorar la recuperación de información.
"""

import logging
import asyncio
from typing import List, Dict, Optional, Set
from langchain_core.messages import HumanMessage
from core.llm_manager import get_fast_llm
from core.memory_manager import search_vector_db_optimized

logger = logging.getLogger(__name__)

class MultiQueryRetriever:
    """
    Implementación de MultiQueryRetriever optimizada para Kognito.
    Genera múltiples consultas reformuladas y combina los resultados.
    """
    
    def __init__(self, num_queries: int = 3, fusion_method: str = "rrf"):
        """
        Inicializa el MultiQueryRetriever.
        
        Args:
            num_queries: Número de consultas alternativas a generar
            fusion_method: Método de fusión ('rrf' para Reciprocal Rank Fusion, 'simple' para concatenación)
        """
        self.num_queries = num_queries
        self.fusion_method = fusion_method
        
    async def generate_alternative_queries(self, original_query: str) -> List[str]:
        """
        Genera consultas alternativas usando el LLM.
        """
        llm = get_fast_llm()
        if not llm:
            logger.warning("LLM no disponible, usando solo la consulta original")
            return [original_query]
            
        prompt = f"""
        Eres un experto en reformular consultas de búsqueda. Tu tarea es generar {self.num_queries} versiones alternativas de la consulta original que capturen diferentes aspectos y perspectivas del mismo tema.

        CONSULTA ORIGINAL: "{original_query}"

        Genera {self.num_queries} consultas alternativas que:
        1. Mantengan la intención original
        2. Usen sinónimos y términos relacionados
        3. Aborden diferentes aspectos del tema
        4. Varíen en especificidad (más general/específica)

        Responde SOLO con las consultas, una por línea, sin numeración ni explicaciones:
        """
        
        try:
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            alternative_queries = [q.strip() for q in response.content.split('\n') if q.strip()]
            
            # Asegurar que tenemos el número correcto de consultas
            if len(alternative_queries) < self.num_queries:
                alternative_queries.extend([original_query] * (self.num_queries - len(alternative_queries)))
            elif len(alternative_queries) > self.num_queries:
                alternative_queries = alternative_queries[:self.num_queries]
                
            logger.info(f"✅ Generadas {len(alternative_queries)} consultas alternativas")
            return alternative_queries
            
        except Exception as e:
            logger.error(f"❌ Error generando consultas alternativas: {e}")
            return [original_query]
    
    async def search_with_multiple_queries(
        self,
        account_id: str,
        original_query: str,
        content_type: Optional[str] = None,
        topics: Optional[List[str]] = None, # Cambiado a plural
        category: Optional[str] = None,
        workspace_id: Optional[str] = None,
        team_id: Optional[str] = None,
        visibility_teams: Optional[List[str]] = None,
        document_ids: Optional[List[str]] = None,
        k: int = 5
    ) -> List[Dict]:
        """
        Realiza búsqueda usando múltiples consultas reformuladas.
        """
        logger.info(f"🔍 Iniciando MultiQuery search para: '{original_query[:50]}...'")
        
        # 1. Generar consultas alternativas
        queries = await self.generate_alternative_queries(original_query)
        logger.info(f"🧠 [Multi-Query RAG] Consultas generadas para la búsqueda: {queries}")
        
        # 2. Ejecutar búsquedas en paralelo
        search_tasks = []
        for query in queries:
            task = search_vector_db_optimized(
                account_id=account_id,
                query=query,
                content_type=content_type,
                topics=topics, # Pasar topics (plural)
                category=category,
                workspace_id=workspace_id,
                team_id=team_id,
                visibility_teams=visibility_teams,
                document_ids=document_ids,
                k=k
            )
            search_tasks.append(task)
        
        try:
            all_results = await asyncio.gather(*search_tasks)
            logger.info(f"✅ Completadas {len(all_results)} búsquedas")
            
            # 3. Fusionar resultados
            if self.fusion_method == "rrf":
                return self._reciprocal_rank_fusion(all_results, k)
            else:
                return self._simple_fusion(all_results, k)
                
        except Exception as e:
            logger.error(f"❌ Error en búsquedas múltiples: {e}")
            # Fallback a búsqueda simple
            return await search_vector_db_optimized(
                account_id=account_id,
                query=original_query,
                content_type=content_type,
                topics=topics, # Pasar topics (plural)
                category=category,
                workspace_id=workspace_id,
                team_id=team_id,
                visibility_teams=visibility_teams,
                document_ids=document_ids,
                k=k
            )
    
    def _reciprocal_rank_fusion(self, all_results: List[List[Dict]], k: int) -> List[Dict]:
        """
        Implementa Reciprocal Rank Fusion para combinar resultados.
        RRF Score = Σ(1 / (rank + 60)) para cada documento en cada lista.
        """
        logger.info("🔄 Aplicando Reciprocal Rank Fusion")
        
        document_scores = {}
        
        for result_list in all_results:
            for rank, doc in enumerate(result_list):
                doc_id = self._get_document_id(doc)
                
                # RRF formula: 1 / (rank + 60)
                rrf_score = 1.0 / (rank + 60)
                
                if doc_id in document_scores:
                    document_scores[doc_id]['score'] += rrf_score
                else:
                    document_scores[doc_id] = {
                        'document': doc,
                        'score': rrf_score
                    }
        
        # Ordenar por score RRF y retornar top-k
        sorted_docs = sorted(
            document_scores.values(),
            key=lambda x: x['score'],
            reverse=True
        )
        
        result = [item['document'] for item in sorted_docs[:k]]
        logger.info(f"✅ RRF completado, retornando {len(result)} documentos únicos")
        return result
    
    def _simple_fusion(self, all_results: List[List[Dict]], k: int) -> List[Dict]:
        """
        Fusión simple: concatena y deduplica resultados.
        """
        logger.info("🔄 Aplicando fusión simple")
        
        seen_docs = set()
        fused_results = []
        
        # Intercalar resultados de diferentes consultas
        max_len = max(len(results) for results in all_results) if all_results else 0
        
        for i in range(max_len):
            for result_list in all_results:
                if i < len(result_list):
                    doc = result_list[i]
                    doc_id = self._get_document_id(doc)
                    
                    if doc_id not in seen_docs:
                        seen_docs.add(doc_id)
                        fused_results.append(doc)
                        
                        if len(fused_results) >= k:
                            break
            
            if len(fused_results) >= k:
                break
        
        logger.info(f"✅ Fusión simple completada, retornando {len(fused_results)} documentos únicos")
        return fused_results[:k]
    
    def _get_document_id(self, doc: Dict) -> str:
        """
        Genera un ID único para un documento basado en su contenido.
        """
        # Usar el contenido del documento como ID único
        content = doc.get('document', '')
        metadata = doc.get('cmetadata', {})
        
        # Crear un hash simple basado en contenido y metadatos clave
        id_parts = [
            content[:100],  # Primeros 100 caracteres
            str(metadata.get('source', '')),
            str(metadata.get('topic', '')),
            str(metadata.get('category', ''))
        ]
        
        return '|'.join(id_parts)


# Función de conveniencia para uso directo
async def multi_query_search(
    account_id: str,
    query: str,
    content_type: Optional[str] = None,
    topics: Optional[List[str]] = None, # Cambiado a plural
    category: Optional[str] = None,
    workspace_id: Optional[str] = None,
    team_id: Optional[str] = None,
    visibility_teams: Optional[List[str]] = None,
    document_ids: Optional[List[str]] = None,
    k: int = 5,
    num_queries: int = 3,
    fusion_method: str = "rrf"
) -> List[Dict]:
    """
    Función de conveniencia para realizar búsqueda con múltiples consultas.
    """
    retriever = MultiQueryRetriever(num_queries=num_queries, fusion_method=fusion_method)
    return await retriever.search_with_multiple_queries(
        account_id=account_id,
        original_query=query,
        content_type=content_type,
        topics=topics, # Pasar topics (plural)
        category=category,
        workspace_id=workspace_id,
        team_id=team_id,
        visibility_teams=visibility_teams,
        document_ids=document_ids,
        k=k
    )
