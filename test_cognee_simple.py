#!/usr/bin/env python3
"""
Test simple para la integración de Cognee.
"""

import asyncio
import sys
import os
import logging

# Añadir el directorio raíz al path
sys.path.append('/app')

from knowledge_graph.cognee_integration import CogneeIntegration
from knowledge_graph.graph_database import GraphDB
from core.config import settings

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_cognee_simple():
    """Test simple de Cognee."""
    logger.info("🧠 Probando integración con Cognee...")
    
    try:
        # Crear instancia de GraphDB
        graph_db = GraphDB(
            uri=settings.neo4j_uri,
            user=settings.neo4j_user,
            password=settings.neo4j_password
        )
        
        # Crear integración con Cognee
        cognee_integration = CogneeIntegration(graph_db)
        
        logger.info(f"📊 Cognee disponible: {cognee_integration.cognee_available}")
        
        # Documentos de prueba
        test_documents = [
            {
                "id": "doc_1",
                "content": "La inteligencia artificial es una tecnología revolucionaria.",
                "metadata": {"source": "test", "type": "article"}
            }
        ]
        
        # Procesar documentos
        result = await cognee_integration.process_documents(test_documents, "test_dataset")
        
        logger.info("✅ Test exitoso!")
        logger.info(f"📊 Método usado: {result.get('method')}")
        logger.info(f"📊 Entidades: {len(result.get('entities', []))}")
        logger.info(f"📊 Relaciones: {len(result.get('relationships', []))}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_cognee_simple())
    sys.exit(0 if success else 1)
