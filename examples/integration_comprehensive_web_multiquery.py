# examples/integration_comprehensive_web_multiquery.py

"""
Ejemplo de integración del MultiQueryRetriever en comprehensive_web_analysis_tool.py
Muestra cómo mejorar la búsqueda en knowledge base usando múltiples consultas.
"""

# Este es un ejemplo de cómo modificar la línea 241 en comprehensive_web_analysis_tool.py

# ANTES (búsqueda simple):
"""
relevant_memories = await search_vector_db_optimized(account_id, web_summary, k=5, workspace_id=workspace_id)
"""

# DESPUÉS (con MultiQueryRetriever):
"""
# Importar al inicio del archivo
from utils.multi_query_retriever import multi_query_search

# En el Step 6: Knowledge Base Integration
logger.info("Step 6: Searching internal knowledge base with MultiQuery...")

# Determinar si usar MultiQuery basado en la complejidad de la consulta
use_multi_query = len(web_summary.split()) > 20 or "análisis" in query.lower() or "investigación" in query.lower()

if use_multi_query:
    logger.info("🚀 Usando MultiQuery para búsqueda exhaustiva en knowledge base")
    relevant_memories = await multi_query_search(
        account_id=account_id,
        query=web_summary,
        content_type="user_documents",  # Buscar en documentos del usuario
        workspace_id=workspace_id,
        k=5,
        num_queries=2,  # Menos consultas para complementar, no dominar
        fusion_method="rrf"
    )
else:
    logger.info("🔍 Usando búsqueda simple para consulta directa")
    relevant_memories = await search_vector_db_optimized(
        account_id=account_id, 
        query=web_summary, 
        k=5, 
        workspace_id=workspace_id
    )

logger.info(f"📚 Knowledge base results: {len(relevant_memories)} documentos encontrados")
"""

# Ejemplo completo de función mejorada
async def enhanced_knowledge_base_search(account_id: str, web_summary: str, query: str, workspace_id: str = None):
    """
    Búsqueda mejorada en knowledge base que decide automáticamente
    entre búsqueda simple y MultiQuery según el contexto.
    """
    from utils.multi_query_retriever import multi_query_search
    from core.memory_manager import search_vector_db_optimized
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Criterios para decidir usar MultiQuery
    query_length = len(web_summary.split())
    complex_keywords = ["análisis", "investigación", "comparación", "evaluación", "estrategia"]
    has_complex_keywords = any(keyword in query.lower() for keyword in complex_keywords)
    
    # Decisión automática
    use_multi_query = (
        query_length > 20 or  # Consultas largas
        has_complex_keywords or  # Palabras clave complejas
        "vs" in query.lower() or  # Comparaciones
        "diferencias" in query.lower() or
        "ventajas" in query.lower()
    )
    
    if use_multi_query:
        logger.info("🚀 Usando MultiQuery para búsqueda exhaustiva en knowledge base")
        logger.info(f"   Criterios: length={query_length}, keywords={has_complex_keywords}")
        
        relevant_memories = await multi_query_search(
            account_id=account_id,
            query=web_summary,
            content_type="user_documents",
            workspace_id=workspace_id,
            k=6,  # Ligeramente más resultados para mejor cobertura
            num_queries=2,  # Consultas moderadas para complementar web
            fusion_method="rrf"
        )
        
        # Log adicional para MultiQuery
        logger.info(f"📊 MultiQuery completado: {len(relevant_memories)} resultados únicos")
        
    else:
        logger.info("🔍 Usando búsqueda simple para consulta directa")
        relevant_memories = await search_vector_db_optimized(
            account_id=account_id,
            query=web_summary,
            k=5,
            workspace_id=workspace_id
        )
    
    logger.info(f"📚 Knowledge base search completed: {len(relevant_memories)} documentos")
    return relevant_memories

# Ejemplo de integración en el contexto completo
async def comprehensive_web_analysis_with_multiquery(query: str, account_id: str, workspace_id: str = None):
    """
    Versión mejorada del análisis web comprehensivo con MultiQuery.
    """
    import logging
    from skills.search_and_research_skill.scripts.web_search_tool import search_and_summarize_web
    from core.llm_manager import get_fast_llm
    
    logger = logging.getLogger(__name__)
    
    try:
        # Steps 1-5: Análisis web normal (sin cambios)
        logger.info("Steps 1-5: Performing web analysis...")
        
        # Simulación del web_summary obtenido en steps anteriores
        web_summary = f"Resumen del análisis web para: {query}"
        
        # Step 6: Knowledge Base Integration MEJORADO
        logger.info("Step 6: Enhanced Knowledge Base Integration...")
        relevant_memories = await enhanced_knowledge_base_search(
            account_id=account_id,
            web_summary=web_summary,
            query=query,
            workspace_id=workspace_id
        )
        
        # Step 7: Final Combined Analysis (mejorado con info de MultiQuery)
        logger.info("Step 7: Performing enhanced combined analysis...")
        final_analysis_llm = get_fast_llm()
        
        if not final_analysis_llm:
            return "Error: El modelo de lenguaje para el análisis final no está disponible."
        
        # Preparar contexto mejorado
        kb_context = ""
        if relevant_memories:
            kb_context = "\n".join([
                f"- {mem.get('document', '')[:200]}..." 
                for mem in relevant_memories[:3]  # Top 3 para no sobrecargar
            ])
        
        enhanced_prompt = f"""
        CONTEXTO CRÍTICO: Estás generando una respuesta de investigación detallada que será enviada directamente al usuario.
        Esta ES la respuesta final que verá el usuario, no un procesamiento interno.

        CONSULTA DEL USUARIO: "{query}"

        INFORMACIÓN WEB ANALIZADA:
        {web_summary}

        CONOCIMIENTO INTERNO RELEVANTE (obtenido con búsqueda {'MultiQuery' if len(relevant_memories) > 5 else 'simple'}):
        {kb_context}

        INSTRUCCIONES:
        1. Combina la información web con el conocimiento interno
        2. Identifica patrones y conexiones entre ambas fuentes
        3. Proporciona insights únicos que surjan de la combinación
        4. Mantén un enfoque equilibrado entre información externa e interna
        5. Responde en español de manera clara y estructurada

        RESPUESTA FINAL:
        """
        
        # Generar respuesta final
        from langchain_core.messages import HumanMessage
        response = await final_analysis_llm.ainvoke([HumanMessage(content=enhanced_prompt)])
        
        return response.content
        
    except Exception as e:
        logger.error(f"❌ Error en análisis web mejorado: {e}", exc_info=True)
        return f"Error durante el análisis: {str(e)}"

# Ejemplo de uso
async def ejemplo_uso():
    """
    Ejemplo de cómo usar la versión mejorada.
    """
    resultado = await comprehensive_web_analysis_with_multiquery(
        query="últimas tendencias en inteligencia artificial para el sector salud",
        account_id="usuario_ejemplo",
        workspace_id="workspace_salud"
    )
    
    print("🎯 Resultado del análisis mejorado:")
    print(resultado)

if __name__ == "__main__":
    import asyncio
    asyncio.run(ejemplo_uso())
