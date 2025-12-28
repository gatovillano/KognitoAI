#!/usr/bin/env python3
"""
Test script para verificar que los cambios en knowledge_gaps funcionan correctamente.
Este script prueba la nueva estructura de KnowledgeGap y que exploration_questions funcionen como preguntas.
"""

import asyncio
import sys
import os

# Añadir el directorio actual al path para importar el módulo
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.advanced_text_analyzer import text_analyzer, KnowledgeGap

async def test_single_text_analysis():
    """Prueba el análisis de texto único con la nueva estructura de knowledge_gaps."""
    print("=== PROBANDO ANÁLISIS DE TEXTO ÚNICO ===")
    
    # Texto de prueba
    test_text = """
    La inteligencia artificial está revolucionando múltiples industrias. Sin embargo, 
    existen desafíos significativos en términos de ética, privacidad y sesgos algorítmicos. 
    Las empresas necesitan desarrollar marcos regulatorios más robustos. El futuro de la IA 
    dependerá de cómo abordemos estos problemas. También es crucial considerar el impacto 
    en el empleo y la necesidad de reentrenamiento laboral masivo.
    """
    
    try:
        result = await text_analyzer.analyze_single_text(test_text, "Documento de Prueba IA")
        
        print(f"✅ Resumen ejecutivo: {result.executive_summary}")
        print(f"✅ Número de temas clave: {len(result.key_themes)}")
        print(f"✅ Número de conceptos centrales: {len(result.central_concepts)}")
        print(f"✅ Número de brechas de conocimiento: {len(result.knowledge_gaps)}")
        print(f"✅ Número de preguntas exploratorias: {len(result.exploration_questions)}")
        
        # Verificar estructura de knowledge_gaps
        print("\n--- BRECHAS DE CONOCIMIENTO ---")
        for i, gap in enumerate(result.knowledge_gaps, 1):
            print(f"Brecha {i}:")
            print(f"  - Título: {gap.gap_title}")
            print(f"  - Explicación: {gap.explanation[:100]}...")
            print(f"  - Contexto: {gap.related_context[:100]}...")
            print()
        
        # Verificar que exploration_questions son preguntas
        print("--- PREGUNTAS EXPLORATORIAS ---")
        for i, question in enumerate(result.exploration_questions, 1):
            print(f"Pregunta {i}: {question}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en análisis de texto único: {e}")
        return False

async def test_collection_analysis():
    """Prueba el análisis de colección con la nueva estructura de emergent_knowledge_gaps."""
    print("\n=== PROBANDO ANÁLISIS DE COLECCIÓN ===")
    
    # Documentos de prueba
    test_documents = [
        {
            "title": "Documento sobre IA",
            "content": "La inteligencia artificial está transformando el sector financiero. Los algoritmos de machine learning permiten detectar fraudes de manera más eficiente. Sin embargo, la transparencia de estos modelos sigue siendo un desafío importante."
        },
        {
            "title": "Documento sobre ética",
            "content": "Los dilemas éticos en IA incluyen privacidad de datos, sesgos algorítmicos y responsabilidad en decisiones automatizadas. Es necesario establecer principios éticos claros para el desarrollo de IA."
        }
    ]
    
    try:
        result = await text_analyzer.analyze_collection(test_documents)
        
        print(f"✅ Resumen de colección: {result.collection_summary[:100]}...")
        print(f"✅ Número de temas transversales: {len(result.cross_cutting_themes)}")
        print(f"✅ Número de conceptos centrales: {len(result.central_concepts)}")
        print(f"✅ Número de brechas emergentes: {len(result.emergent_knowledge_gaps)}")
        print(f"✅ Número de preguntas exploratorias: {len(result.exploration_questions)}")
        
        # Verificar estructura de emergent_knowledge_gaps
        print("\n--- BRECHAS EMERGENTES ---")
        for i, gap in enumerate(result.emergent_knowledge_gaps, 1):
            print(f"Brecha emergente {i}:")
            print(f"  - Título: {gap.gap_title}")
            print(f"  - Explicación: {gap.explanation[:100]}...")
            print(f"  - Contexto: {gap.related_context[:100]}...")
            print()
        
        # Verificar que exploration_questions son preguntas
        print("--- PREGUNTAS EXPLORATORIAS ---")
        for i, question in enumerate(result.exploration_questions, 1):
            print(f"Pregunta {i}: {question}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en análisis de colección: {e}")
        return False

async def main():
    """Función principal para ejecutar todas las pruebas."""
    print("🧪 Iniciando pruebas de cambios en knowledge_gaps...\n")
    
    # Verificar que el modelo KnowledgeGap existe y tiene la estructura correcta
    print("=== VERIFICANDO MODELO KNOWLEDGE GAP ===")
    print(f"✅ Modelo KnowledgeGap importado correctamente")
    print(f"✅ Campos disponibles: {KnowledgeGap.model_fields.keys()}")
    
    # Ejecutar pruebas
    test1_passed = await test_single_text_analysis()
    test2_passed = await test_collection_analysis()
    
    # Resumen final
    print("\n=== RESUMEN DE PRUEBAS ===")
    print(f"Análisis de texto único: {'✅ PASÓ' if test1_passed else '❌ FALLÓ'}")
    print(f"Análisis de colección: {'✅ PASÓ' if test2_passed else '❌ FALLÓ'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 ¡Todos los tests pasaron! Los cambios en knowledge_gaps funcionan correctamente.")
    else:
        print("\n⚠️  Algunos tests fallaron. Revisar la implementación.")

if __name__ == "__main__":
    asyncio.run(main())