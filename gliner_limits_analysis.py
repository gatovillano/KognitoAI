#!/usr/bin/env python3
"""
Análisis de límites de GLiNER y propuesta de mejoras.
"""

def analyze_gliner_limits():
    """Analiza los límites actuales de GLiNER en nuestro código."""
    
    print("🔍 ANÁLISIS DE LÍMITES DE GLINER")
    print("=" * 50)
    
    # Límites actuales en nuestro código
    current_limits = {
        "chars_per_chunk": 350,
        "max_chunks_per_doc": 10,
        "entity_labels_count": 18,  # En nuestro código
        "threshold_default": 0.5
    }
    
    print("📊 LÍMITES ACTUALES EN NUESTRO CÓDIGO:")
    for key, value in current_limits.items():
        print(f"   • {key}: {value}")
    
    print("\n🎯 LÍMITES RECOMENDADOS POR GLINER:")
    recommended_limits = {
        "chars_per_prediction": 384,
        "max_entity_types": 20,
        "max_entities_per_prediction": "Sin límite estricto (pero rendimiento se degrada)",
        "optimal_chunk_size": "200-300 caracteres"
    }
    
    for key, value in recommended_limits.items():
        print(f"   • {key}: {value}")
    
    print("\n⚡ PROPUESTA DE MEJORAS:")
    improvements = [
        "Agregar parámetro max_entities_per_chunk (ej: 50)",
        "Implementar paginación si se excede el límite",
        "Agregar logging de entidades extraídas por chunk",
        "Configurar umbral adaptativo según longitud del texto"
    ]
    
    for i, improvement in enumerate(improvements, 1):
        print(f"   {i}. {improvement}")
    
    print("\n💡 RESPUESTA DIRECTA:")
    print("   GLiNER NO tiene un límite máximo hard-coded para entidades,")
    print("   pero nuestro código podría beneficiarse de límites adicionales")
    print("   para garantizar rendimiento óptimo.")

if __name__ == "__main__":
    analyze_gliner_limits()