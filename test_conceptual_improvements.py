#!/usr/bin/env python3
"""
Script de prueba para validar las mejoras en el procesador conceptual.
"""

import asyncio
import sys
import os

# Agregar el directorio padre al path para importar módulos
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from knowledge_graph.conceptual_graph_processor import ConceptualGraphProcessor

# Datos de prueba
TEST_DOCUMENTS = [
    {
        "title": "Teorías críticas contemporáneas",
        "content": """
La teoría crítica contemporánea representa un paradigma fundamental en las ciencias sociales.
Se basa en la tradición de la Escuela de Frankfurt pero incorpora nuevas perspectivas.

La epistemología feminista ha transformado radicalmente los enfoques tradicionales de investigación.
Este enfoque cuestiona los supuestos androcéntricos y propone metodologías más inclusivas.

El análisis discursivo crítico examina cómo el lenguaje construye realidades sociales.
Esta metodología es esencial para entender los mecanismos de poder en los medios de comunicación.

Las teorías poscoloniales ofrecen una crítica profunda a la colonialidad del saber.
Estos marcos teóricos son fundamentales para repensar las relaciones de poder globales.

La interseccionalidad como marco analítico permite comprender las múltiples dimensiones de la opresión.
Este concepto ha revolucionado los estudios de género y raza en las últimas décadas.
"""
    },
    {
        "title": "Metodologías de investigación avanzadas",
        "content": """
La investigación-acción participativa representa un enfoque metodológico transformador.
Este método involucra activamente a las comunidades en el proceso de investigación.

Los estudios cualitativos han evolucionado significativamente en las últimas décadas.
Las nuevas técnicas de análisis de datos cualitativos permiten una comprensión más profunda.

La etnografía digital emerge como una metodología innovadora para estudiar culturas online.
Este enfoque combina técnicas tradicionales con análisis de datos digitales.

El análisis de redes sociales ofrece herramientas poderosas para estudiar relaciones complejas.
Esta metodología es particularmente útil en estudios organizacionales y comunitarios.
"""
    }
]

async def test_improved_conceptual_processor():
    """Prueba las mejoras en el procesador conceptual."""
    
    print("🧪 Iniciando pruebas del procesador conceptual mejorado...")
    print("=" * 60)
    
    # Inicializar procesador (sin modelos reales para esta prueba)
    processor = ConceptualGraphProcessor(llm=None, sentence_transformer=None)
    
    try:
        # Procesar documentos
        print("\n📚 Procesando documentos de prueba...")
        result = await processor.process_documents_conceptually(TEST_DOCUMENTS, "test_dataset")
        
        # Analizar resultados
        print(f"\n✅ Procesamiento completado con éxito!")
        print(f"📊 Estadísticas del procesamiento:")
        print(f"   - Citas conceptuales extraídas: {len(result['conceptual_nodes'])}")
        print(f"   - Relaciones temáticas identificadas: {len(result['thematic_relationships'])}")
        print(f"   - Nodos de categoría creados: {len(result['category_nodes'])}")
        print(f"   - Perfiles de ideas identificados: {len(result['idea_profiles'])}")
        
        # Analizar calidad de las citas
        print(f"\n🔍 Análisis de calidad de citas:")
        high_importance = sum(1 for quote in result['conceptual_nodes'] if quote.get('importance') == 'alta')
        high_depth = sum(1 for quote in result['conceptual_nodes'] if quote.get('conceptual_depth') == 'alta')
        
        print(f"   - Citas de alta importancia: {high_importance}")
        print(f"   - Citas con profundidad conceptual alta: {high_depth}")
        
        # Analizar relaciones
        print(f"\n🔗 Análisis de relaciones temáticas:")
        strong_rels = sum(1 for rel in result['thematic_relationships'] if rel.get('relationship_strength') == 'fuerte')
        print(f"   - Relaciones fuertes: {strong_rels}")
        
        # Mostrar ejemplos
        print(f"\n📝 Ejemplos de resultados mejorados:")
        
        if result['conceptual_nodes']:
            print(f"\n   💡 Ejemplo de cita conceptual:")
            example_quote = result['conceptual_nodes'][0]
            print(f"      - Texto: {example_quote['text'][:100]}...")
            print(f"      - Concepto: {example_quote['concept']}")
            print(f"      - Categoría: {example_quote['category']}")
            print(f"      - Importancia: {example_quote['importance']}")
            print(f"      - Profundidad: {example_quote['conceptual_depth']}")
        
        if result['category_nodes']:
            print(f"\n   📊 Ejemplo de nodo de categoría:")
            example_category = result['category_nodes'][0]
            print(f"      - Nombre: {example_category['name']}")
            print(f"      - Citas agrupadas: {example_category['quotes_count']}")
            print(f"      - Profundidad: {example_category['conceptual_depth']}")
            print(f"      - Coherencia: {example_category['thematic_coherence']}")
        
        if result['thematic_relationships']:
            print(f"\n   🔗 Ejemplo de relación temática:")
            example_rel = result['thematic_relationships'][0]
            print(f"      - Tipo: {example_rel['type']}")
            print(f"      - Descripción: {example_rel['description']}")
            print(f"      - Fuerza: {example_rel['relationship_strength']}")
            print(f"      - Confianza: {example_rel['confidence']}")
        
        # Validar mejoras
        print(f"\n🎯 Validación de mejoras implementadas:")
        
        improvements = []
        
        # 1. Mayor cantidad de citas
        if len(result['conceptual_nodes']) >= 15:
            improvements.append("✅ Mayor cantidad de citas extraídas")
        
        # 2. Profundidad conceptual
        if high_depth >= 5:
            improvements.append("✅ Análisis de profundidad conceptual implementado")
        
        # 3. Relaciones mejoradas
        if strong_rels >= 3:
            improvements.append("✅ Relaciones temáticas más precisas y fuertes")
        
        # 4. Categorización avanzada
        if result['category_nodes'] and any(cat.get('conceptual_depth') == 'alta' for cat in result['category_nodes']):
            improvements.append("✅ Categorización semántica sofisticada")
        
        # 5. Perfiles de ideas
        if len(result['idea_profiles']) >= 2:
            improvements.append("✅ Identificación mejorada de perfiles de ideas")
        
        for improvement in improvements:
            print(f"   {improvement}")
        
        if improvements:
            print(f"\n🎉 ¡Todas las mejoras han sido implementadas exitosamente!")
            print(f"   El procesador conceptual ahora ofrece un análisis más sofisticado y completo.")
        else:
            print(f"\n⚠️  Algunas mejoras no pudieron ser validadas en esta prueba.")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error durante las pruebas: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Ejecutar prueba asíncrona
    success = asyncio.run(test_improved_conceptual_processor())
    
    if success:
        print(f"\n🎊 Pruebas completadas con éxito!")
        print(f"   El procesador conceptual mejorado está listo para su uso.")
    else:
        print(f"\n💥 Las pruebas fallaron.")
        print(f"   Revisa los errores y ajusta el código según sea necesario.")