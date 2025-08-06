#!/usr/bin/env python3
"""
Script de prueba para la herramienta CogneeConceptualProcessingTool.

Este script permite testear la funcionalidad de procesamiento conceptual
de documentos usando Cognee y Neo4j.
"""

import asyncio
import logging
import sys
import os
import uuid

# Agregar el directorio raíz al path para importar módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.cognee_conceptual_processing_tool import CogneeConceptualProcessingTool

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_cognee_conceptual_processing():
    """
    Función principal para testear la herramienta de procesamiento conceptual.
    """
    print("🧠 === PRUEBA DE COGNEE CONCEPTUAL PROCESSING TOOL ===")
    print()
    
    # Crear instancia de la herramienta
    try:
        print("📝 Creando instancia de CogneeConceptualProcessingTool...")
        tool = CogneeConceptualProcessingTool()
        print("✅ Herramienta creada exitosamente")
        print()
        
        # Verificar si la integración con Cognee está disponible
        if tool.cognee_integration is None:
            print("❌ La integración con Cognee no está disponible.")
            print("   Verifica que:")
            print("   - Neo4j esté corriendo (docker compose up -d neo4j)")
            print("   - Las variables NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD estén en .env")
            return False
        
        print("✅ Integración con Cognee disponible")
        print()
        
        # Datos de prueba - usar UUID válido
        account_id = str(uuid.uuid4())
        
        # Opción 1: Documentos con contenido directo
        test_documents = [
            {
                "title": "Inteligencia Artificial - Conceptos Básicos",
                "content": """
                La inteligencia artificial (IA) es una rama de la informática que se centra en crear sistemas 
                capaces de realizar tareas que normalmente requieren inteligencia humana. Estos sistemas pueden 
                aprender, razonar, percibir y tomar decisiones.
                
                Los principales tipos de IA incluyen:
                - IA débil o estrecha: diseñada para tareas específicas
                - IA general: capaz de realizar cualquier tarea intelectual humana
                - IA superinteligente: supera la inteligencia humana en todos los aspectos
                
                Las aplicaciones actuales de la IA incluyen reconocimiento de voz, visión por computadora,
                procesamiento de lenguaje natural y sistemas de recomendación.
                """
            },
            {
                "title": "Machine Learning - Fundamentos",
                "content": """
                El aprendizaje automático (Machine Learning) es un subconjunto de la inteligencia artificial
                que permite a las máquinas aprender y mejorar automáticamente a partir de la experiencia
                sin ser programadas explícitamente.
                
                Los principales tipos de aprendizaje automático son:
                - Aprendizaje supervisado: usa datos etiquetados para entrenar modelos
                - Aprendizaje no supervisado: encuentra patrones en datos sin etiquetas
                - Aprendizaje por refuerzo: aprende a través de interacciones y recompensas
                
                Las técnicas comunes incluyen redes neuronales, árboles de decisión, 
                máquinas de vectores de soporte y algoritmos de clustering.
                """
            }
        ]
        
        print("📄 Documentos de prueba preparados:")
        for i, doc in enumerate(test_documents, 1):
            print(f"   {i}. {doc['title']}")
        print()
        
        # Ejecutar procesamiento conceptual
        print("🔄 Ejecutando procesamiento conceptual...")
        print("   (Esto puede tomar unos minutos...)")
        
        result = await tool._arun(
            account_id=account_id,
            documents=test_documents,
            dataset_name="test_conceptual_processing"
        )
        
        print()
        print("📊 === RESULTADOS DEL PROCESAMIENTO ===")
        print()
        
        if result.get("status") == "error":
            print(f"❌ Error durante el procesamiento: {result.get('error')}")
            print(f"   Detalles: {result.get('details')}")
            return False
        
        # Mostrar resultados
        print("✅ Procesamiento completado exitosamente!")
        print()
        
        if "summary" in result:
            print("📝 Resumen:")
            print(f"   {result['summary']}")
            print()
        
        if "entities_processed" in result:
            print(f"🏷️  Entidades procesadas: {result['entities_processed']}")
        
        if "relationships_created" in result:
            print(f"🔗 Relaciones creadas: {result['relationships_created']}")
        
        if "concepts_extracted" in result:
            print(f"💡 Conceptos extraídos: {result['concepts_extracted']}")
        
        if "citations" in result:
            print(f"📖 Citas identificadas: {len(result['citations'])}")
            if result['citations']:
                print("   Ejemplos de citas:")
                for i, citation in enumerate(result['citations'][:3], 1):
                    print(f"   {i}. {citation.get('text', 'N/A')[:100]}...")
        
        print()
        print("🎉 ¡Prueba completada exitosamente!")
        return True
        
    except Exception as e:
        print(f"❌ Error durante la prueba: {e}")
        logger.error(f"Error en test_cognee_conceptual_processing: {e}", exc_info=True)
        return False

def test_tool_sync():
    """
    Función para testear la herramienta de forma síncrona.
    """
    print("🧠 === PRUEBA SÍNCRONA DE COGNEE CONCEPTUAL PROCESSING TOOL ===")
    print()
    
    try:
        # Crear instancia de la herramienta
        print("📝 Creando instancia de CogneeConceptualProcessingTool...")
        tool = CogneeConceptualProcessingTool()
        print("✅ Herramienta creada exitosamente")
        print()
        
        # Verificar si la integración está disponible
        if tool.cognee_integration is None:
            print("❌ La integración con Cognee no está disponible.")
            return False
        
        # Datos de prueba simples
        account_id = "test_account_sync"
        test_documents = [
            {
                "title": "Documento de Prueba",
                "content": "Este es un documento de prueba para verificar que la herramienta funciona correctamente."
            }
        ]
        
        print("🔄 Ejecutando procesamiento síncrono...")
        result = tool._run(
            account_id=account_id,
            documents=test_documents,
            dataset_name="test_sync"
        )
        
        print("📊 Resultado:")
        if result.get("status") == "error":
            print(f"❌ Error: {result.get('error')}")
            return False
        else:
            print("✅ Procesamiento síncrono exitoso!")
            return True
            
    except Exception as e:
        print(f"❌ Error en prueba síncrona: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Iniciando pruebas de CogneeConceptualProcessingTool...")
    print()
    
    # Verificar que Neo4j esté corriendo
    print("🔍 Verificando estado de Neo4j...")
    import subprocess
    try:
        result = subprocess.run(["docker", "ps", "--filter", "name=neo4j"], 
                              capture_output=True, text=True)
        if "neo4j" in result.stdout:
            print("✅ Neo4j está corriendo")
        else:
            print("❌ Neo4j no está corriendo. Ejecuta: docker compose up -d neo4j")
            sys.exit(1)
    except Exception as e:
        print(f"⚠️ No se pudo verificar el estado de Neo4j: {e}")
    
    print()
    
    # Ejecutar pruebas
    print("1️⃣ Ejecutando prueba síncrona...")
    sync_success = test_tool_sync()
    print()
    
    print("2️⃣ Ejecutando prueba asíncrona...")
    async_success = asyncio.run(test_cognee_conceptual_processing())
    
    print()
    print("📋 === RESUMEN DE PRUEBAS ===")
    print(f"   Prueba síncrona: {'✅ EXITOSA' if sync_success else '❌ FALLÓ'}")
    print(f"   Prueba asíncrona: {'✅ EXITOSA' if async_success else '❌ FALLÓ'}")
    
    if sync_success and async_success:
        print()
        print("🎉 ¡Todas las pruebas pasaron exitosamente!")
        print("   La herramienta CogneeConceptualProcessingTool está funcionando correctamente.")
    else:
        print()
        print("⚠️ Algunas pruebas fallaron. Revisa los logs para más detalles.")
        sys.exit(1)
