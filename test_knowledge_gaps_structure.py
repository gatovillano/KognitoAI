#!/usr/bin/env python3
"""
Test simplificado para verificar que la estructura de KnowledgeGap es correcta.
"""

import sys
import os

# Añadir el directorio actual al path para importar el módulo
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.advanced_text_analyzer import KnowledgeGap, SingleTextAnalysis, CollectionAnalysis

def test_knowledge_gap_structure():
    """Verifica que la estructura de KnowledgeGap sea correcta."""
    print("=== PROBANDO ESTRUCTURA DE KNOWLEDGE GAP ===")
    
    try:
        # Crear una instancia de KnowledgeGap
        gap_data = {
            "gap_title": "Brecha en transparencia algorítmica",
            "explanation": "El texto menciona que la transparencia de los modelos de IA es un desafío, pero no proporciona detalles específicos sobre cómo abordar este problema. Esta brecha es importante porque afecta la confianza y adopción de sistemas de IA en sectores críticos.",
            "related_context": "El contexto surge al discutir los desafíos éticos en el desarrollo de inteligencia artificial, específicamente en el sector financiero."
        }
        
        gap = KnowledgeGap(**gap_data)
        
        print(f"✅ Gap title: {gap.gap_title}")
        print(f"✅ Explanation: {gap.explanation[:100]}...")
        print(f"✅ Related context: {gap.related_context[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creando KnowledgeGap: {e}")
        return False

def test_models_contain_knowledge_gaps():
    """Verifica que los modelos contengan los campos correctos."""
    print("\n=== PROBANDO MODELOS ===")
    
    try:
        # Verificar SingleTextAnalysis
        single_fields = list(SingleTextAnalysis.model_fields.keys())
        print(f"✅ SingleTextAnalysis campos: {single_fields}")
        
        if 'knowledge_gaps' in single_fields:
            knowledge_gaps_field = SingleTextAnalysis.model_fields['knowledge_gaps']
            print(f"✅ knowledge_gaps en SingleTextAnalysis: {knowledge_gaps_field.annotation}")
        else:
            print("❌ knowledge_gaps no encontrado en SingleTextAnalysis")
            return False
            
        # Verificar CollectionAnalysis  
        collection_fields = list(CollectionAnalysis.model_fields.keys())
        print(f"✅ CollectionAnalysis campos: {collection_fields}")
        
        if 'emergent_knowledge_gaps' in collection_fields:
            emergent_gaps_field = CollectionAnalysis.model_fields['emergent_knowledge_gaps']
            print(f"✅ emergent_knowledge_gaps en CollectionAnalysis: {emergent_gaps_field.annotation}")
        else:
            print("❌ emergent_knowledge_gaps no encontrado en CollectionAnalysis")
            return False
            
        # Verificar exploration_questions
        if 'exploration_questions' in single_fields and 'exploration_questions' in collection_fields:
            print("✅ exploration_questions presente en ambos modelos")
        else:
            print("❌ exploration_questions faltante en algún modelo")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Error verificando modelos: {e}")
        return False

def main():
    """Función principal."""
    print("🧪 Verificando estructura de knowledge_gaps...\n")
    
    test1_passed = test_knowledge_gap_structure()
    test2_passed = test_models_contain_knowledge_gaps()
    
    print("\n=== RESUMEN ===")
    print(f"Estructura KnowledgeGap: {'✅ CORRECTA' if test1_passed else '❌ INCORRECTA'}")
    print(f"Modelos actualizados: {'✅ CORRECTOS' if test2_passed else '❌ INCORRECTOS'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 ¡Verificación exitosa! La estructura de knowledge_gaps es correcta.")
    else:
        print("\n⚠️  Hay problemas con la estructura. Revisar implementación.")

if __name__ == "__main__":
    main()