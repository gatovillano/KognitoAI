#!/usr/bin/env python3
"""
Ejemplos de uso de las herramientas de Grafo de Conocimiento en KognitoAI.
Demuestra diferentes casos de uso para grafos de conocimiento.
"""

import asyncio
import sys
import os
import logging

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from skills.knowledge_and_memory_skill.scripts.conceptual_processing_tool import ConceptualProcessingTool
from skills.knowledge_and_memory_skill.scripts.knowledge_graph_tool import KnowledgeGraphTool
from skills.analysis_and_insights_skill.scripts.insight_generation_tool import InsightGenerationTool

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def example_1_process_research_documents():
    """Ejemplo 1: Procesar documentos de investigación y crear grafo."""
    
    print("🔬 Ejemplo 1: Procesando documentos de investigación")
    print("=" * 60)
    
    # Crear la herramienta
    tool = ConceptualProcessingTool(account_id="researcher_001")
    
    # Documentos de ejemplo sobre IA y Machine Learning
    research_documents = [
        {
            "id": "paper_1",
            "title": "Transformers: Attention Is All You Need",
            "content": """
            Los Transformers han revolucionado el procesamiento del lenguaje natural.
            La arquitectura se basa completamente en mecanismos de atención, eliminando
            la necesidad de redes recurrentes y convolucionales. El modelo utiliza
            atención multi-cabeza para procesar secuencias de manera paralela.
            """,
            "metadata": {
                "authors": ["Vaswani et al."],
                "year": 2017,
                "venue": "NIPS",
                "keywords": ["transformers", "attention", "nlp"]
            }
        },
        {
            "id": "paper_2", 
            "title": "BERT: Pre-training of Deep Bidirectional Transformers",
            "content": """
            BERT introduce el concepto de pre-entrenamiento bidireccional usando
            Transformers. A diferencia de modelos anteriores que procesan texto
            de izquierda a derecha, BERT puede considerar el contexto completo
            de ambas direcciones. Esto se logra mediante masked language modeling.
            """,
            "metadata": {
                "authors": ["Devlin et al."],
                "year": 2018,
                "venue": "NAACL",
                "keywords": ["bert", "bidirectional", "pre-training"]
            }
        },
        {
            "id": "paper_3",
            "title": "GPT-3: Language Models are Few-Shot Learners", 
            "content": """
            GPT-3 demuestra que los modelos de lenguaje grandes pueden realizar
            tareas sin entrenamiento específico, usando solo ejemplos en el contexto.
            Con 175 mil millones de parámetros, GPT-3 muestra capacidades emergentes
            en razonamiento, traducción y generación de código.
            """,
            "metadata": {
                "authors": ["Brown et al."],
                "year": 2020,
                "venue": "NeurIPS",
                "keywords": ["gpt-3", "few-shot", "large language models"]
            }
        }
    ]
    
    # Procesar documentos
    result = await tool._arun(
        documents=research_documents,
        dataset_name="ai_research"
    )
    
    print("📊 Resultado del procesamiento:")
    print(result)
    print("
" + "=" * 60)

async def example_2_search_knowledge_graph():
    """Ejemplo 2: Buscar información específica en el grafo."""
    
    print("🔍 Ejemplo 2: Buscando en el grafo de conocimiento")
    print("=" * 60)
    
    tool = KnowledgeGraphTool(account_id="researcher_001")
    
    # Diferentes tipos de consultas
    queries = [
        "¿Qué es la atención en Transformers?",
        "Diferencias entre BERT y GPT-3",
        "Aplicaciones de few-shot learning",
        "Evolución de los modelos de lenguaje"
    ]
    
    for query in queries:
        print(f"
🔍 Consulta: {query}")
        print("-" * 40)
        
        result = await tool._arun(
            natural_language_query=query
        )
        
        print(result)
    
    print("
" + "=" * 60)

async def example_3_get_insights():
    """Ejemplo 3: Obtener insights y patrones del grafo."""
    
    print("💡 Ejemplo 3: Obteniendo insights del grafo")
    print("=" * 60)
    
    tool = InsightGenerationTool(account_id="researcher_001")
    
    # Consultas para insights
    insight_queries = [
        "modelos de lenguaje",
        "arquitecturas de redes neuronales", 
        "técnicas de pre-entrenamiento",
        "aplicaciones de IA"
    ]
    
    for query in insight_queries:
        print(f"
💡 Insights sobre: {query}")
        print("-" * 40)
        
        result = await tool._arun(
            query=query,
            account_id="researcher_001"
        )
        
        print(result)
    
    print("
" + "=" * 60)

async def example_4_business_documents():
    """Ejemplo 4: Procesar documentos empresariales."""
    
    print("💼 Ejemplo 4: Procesando documentos empresariales")
    print("=" * 60)
    
    processing_tool = ConceptualProcessingTool(account_id="company_abc")
    search_tool = KnowledgeGraphTool(account_id="company_abc")
    
    # Documentos empresariales de ejemplo
    business_docs = [
        {
            "id": "strategy_2024",
            "title": "Estrategia Digital 2024",
            "content": """
            Nuestra estrategia digital se enfoca en tres pilares principales:
            1. Transformación de procesos mediante automatización con IA
            2. Mejora de la experiencia del cliente con chatbots inteligentes
            3. Análisis predictivo para optimización de inventarios
            
            Objetivos clave: reducir costos operativos en 20%, aumentar
            satisfacción del cliente al 95%, y mejorar precisión de forecasting.
            """,
            "metadata": {
                "department": "Strategy",
                "year": 2024,
                "priority": "high"
            }
        },
        {
            "id": "market_analysis",
            "title": "Análisis de Mercado Q1 2024",
            "content": """
            El mercado muestra tendencias hacia la personalización y sostenibilidad.
            Los competidores principales están invirtiendo en tecnologías verdes
            y experiencias personalizadas. Oportunidades identificadas en el
            segmento de millennials y Gen Z que valoran la responsabilidad social.
            """,
            "metadata": {
                "department": "Marketing",
                "quarter": "Q1",
                "year": 2024
            }
        }
    ]
    
    # Procesar documentos empresariales
    result = await processing_tool._arun(
        documents=business_docs,
        dataset_name="business_strategy"
    )
    
    print("📊 Resultado del procesamiento empresarial:")
    print(result)
    
    # Buscar información específica
    print(f"
🔍 Buscando estrategias de IA...")
    search_result = await search_tool._arun(
        natural_language_query="estrategias de inteligencia artificial"
    )
    
    print(search_result)
    print("
" + "=" * 60)

async def run_all_examples():
    """Ejecuta todos los ejemplos en secuencia."""
    
    print("🧠 Ejemplos de Uso de las Herramientas de Grafo de Conocimiento en KognitoAI")
    print("=" * 80)
    print("Estos ejemplos demuestran cómo usar las nuevas herramientas para crear y consultar")
    print("grafos de conocimiento con diferentes tipos de documentos.")
    print("=" * 80)
    
    try:
        # Ejecutar ejemplos
        await example_1_process_research_documents()
        await example_2_search_knowledge_graph()
        await example_3_get_insights()
        await example_4_business_documents()
        
        print("✅ Todos los ejemplos completados exitosamente!")
        print("
💡 Próximos pasos:")
        print("1. Accede a Neo4j Browser (http://localhost:7474) para visualizar el grafo")
        print("2. Experimenta con tus propios documentos")
        print("3. Integra las herramientas de grafo de conocimiento en tu flujo de trabajo")
        
    except Exception as e:
        logger.error(f"❌ Error ejecutando ejemplos: {e}")
        print(f"
❌ Error: {e}")
        print("
🔧 Soluciones posibles:")
        print("1. Verifica que Neo4j esté corriendo: docker-compose up -d neo4j")
        print("2. Revisa tu configuración en .env (NEO4J_*, OPENAI_API_KEY, etc)")
        print("3. Asegúrate de que el servicio core esté activo")

if __name__ == "__main__":
    asyncio.run(run_all_examples())
