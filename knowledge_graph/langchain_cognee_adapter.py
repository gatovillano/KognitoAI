"""
Adapter para integrar langchain-cognee con KognitoAI.
Proporciona una interfaz más robusta y estandardizada para el procesamiento de grafos de conocimiento.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class LangChainCogneeAdapter:
    """
    Adapter que utiliza langchain-cognee para procesamiento de grafos de conocimiento.
    Proporciona una interfaz más robusta que nuestra implementación personalizada.
    """
    
    def __init__(self, graph_db, llm_manager=None):
        """
        Inicializa el adapter de langchain-cognee.
        
        Args:
            graph_db: Instancia de GraphDB para conectar con Neo4j
            llm_manager: Manager de LLM para procesamiento
        """
        self.graph_db = graph_db
        self.llm_manager = llm_manager
        self._cognee_instance = None
        logger.info("✅ LangChainCogneeAdapter inicializado")
    
    async def _initialize_cognee(self):
        """Inicializa la instancia de langchain-cognee si no existe."""
        if self._cognee_instance is None:
            try:
                # Importar langchain-cognee
                from langchain_cognee import CogneeGraphProcessor
                
                # Configurar con nuestros parámetros
                self._cognee_instance = CogneeGraphProcessor(
                    neo4j_uri=self.graph_db.uri,
                    neo4j_user=self.graph_db.user,
                    neo4j_password=self.graph_db.password,
                    llm=self.llm_manager.get_main_llm() if self.llm_manager else None
                )
                
                logger.info("✅ Instancia de langchain-cognee inicializada")
                
            except ImportError:
                logger.error("❌ langchain-cognee no está instalado. Instalar con: pip install langchain-cognee")
                raise
            except Exception as e:
                logger.error(f"❌ Error inicializando langchain-cognee: {e}")
                raise
    
    async def process_documents_with_langchain_cognee(
        self, 
        documents: List[Dict[str, Any]], 
        workspace_name: str = "default"
    ) -> Dict[str, Any]:
        """
        Procesa documentos usando langchain-cognee.
        
        Args:
            documents: Lista de documentos a procesar
            workspace_name: Nombre del workspace
            
        Returns:
            Dict con estadísticas del procesamiento
        """
        try:
            await self._initialize_cognee()
            
            logger.info(f"🚀 Procesando {len(documents)} documentos con langchain-cognee...")
            
            # Convertir documentos al formato esperado por langchain-cognee
            formatted_docs = []
            for doc in documents:
                formatted_docs.append({
                    "content": doc.get("content", ""),
                    "metadata": {
                        "title": doc.get("title", ""),
                        "source": doc.get("source", ""),
                        "workspace": workspace_name,
                        "processed_at": datetime.now().isoformat()
                    }
                })
            
            # Procesar con langchain-cognee
            results = await self._cognee_instance.process_documents(formatted_docs)
            
            logger.info(f"✅ Procesamiento completado con langchain-cognee")
            
            return {
                "entities_processed": results.get("entities_count", 0),
                "relationships_processed": results.get("relationships_count", 0),
                "status": "success",
                "processor": "langchain-cognee",
                "workspace": workspace_name
            }
            
        except Exception as e:
            logger.error(f"❌ Error procesando con langchain-cognee: {e}")
            raise
    
    async def query_knowledge_graph(
        self, 
        query: str, 
        workspace_name: str = "default"
    ) -> List[Dict[str, Any]]:
        """
        Consulta el grafo de conocimiento usando langchain-cognee.
        
        Args:
            query: Consulta en lenguaje natural
            workspace_name: Nombre del workspace
            
        Returns:
            Lista de resultados
        """
        try:
            await self._initialize_cognee()
            
            logger.info(f"🔍 Consultando grafo con: '{query}'")
            
            # Usar langchain-cognee para consultar
            results = await self._cognee_instance.query(
                query=query,
                workspace=workspace_name
            )
            
            logger.info(f"✅ Consulta completada: {len(results)} resultados")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error consultando grafo: {e}")
            raise
    
    async def get_graph_statistics(self, workspace_name: str = "default") -> Dict[str, Any]:
        """
        Obtiene estadísticas del grafo de conocimiento.
        
        Args:
            workspace_name: Nombre del workspace
            
        Returns:
            Dict con estadísticas
        """
        try:
            await self._initialize_cognee()
            
            # Usar langchain-cognee para obtener estadísticas
            stats = await self._cognee_instance.get_statistics(workspace=workspace_name)
            
            return {
                "nodes_count": stats.get("nodes", 0),
                "relationships_count": stats.get("relationships", 0),
                "workspace": workspace_name,
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo estadísticas: {e}")
            return {
                "nodes_count": 0,
                "relationships_count": 0,
                "workspace": workspace_name,
                "error": str(e)
            }
    
    async def clear_workspace(self, workspace_name: str) -> bool:
        """
        Limpia un workspace específico.
        
        Args:
            workspace_name: Nombre del workspace a limpiar
            
        Returns:
            True si se limpió correctamente
        """
        try:
            await self._initialize_cognee()
            
            logger.info(f"🧹 Limpiando workspace: {workspace_name}")
            
            # Usar langchain-cognee para limpiar
            await self._cognee_instance.clear_workspace(workspace_name)
            
            logger.info(f"✅ Workspace '{workspace_name}' limpiado")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error limpiando workspace: {e}")
            return False
