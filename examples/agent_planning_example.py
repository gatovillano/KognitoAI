# examples/agent_planning_example.py

"""
Ejemplo de cómo funciona la nueva fase de planificación del agente.
Demuestra el proceso de "pensamiento" antes de ejecutar herramientas.
"""

import asyncio
import logging
from core.agent import create_execution_plan

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def ejemplo_consulta_simple():
    """
    Ejemplo con una consulta simple que requiere una sola herramienta.
    """
    print("🧠 Ejemplo: Consulta Simple")
    print("=" * 50)
    
    user_query = "¿Qué documentos tengo sobre machine learning?"
    context = "Usuario preguntando por documentos específicos"
    
    print(f"👤 Usuario: {user_query}")
    print(f"📝 Contexto: {context}")
    
    try:
        plan = await create_execution_plan(user_query, context)
        
        print(f"\n🧠 Análisis del agente:")
        analysis = plan.get("query_analysis", {})
        print(f"   Tipo: {analysis.get('type', 'unknown')}")
        print(f"   Complejidad: {analysis.get('complexity', 0)}/5")
        print(f"   Intención: {analysis.get('intent', 'N/A')}")
        
        strategy = plan.get("execution_strategy", {})
        print(f"\n📋 Estrategia:")
        print(f"   Herramienta principal: {strategy.get('primary_tool', 'N/A')}")
        print(f"   Herramienta de respaldo: {strategy.get('fallback_tool', 'N/A')}")
        print(f"   Razonamiento: {strategy.get('reasoning', 'N/A')}")
        
        user_msg = plan.get("user_message", {})
        print(f"\n💭 Pensamiento visible:")
        print(f"   {user_msg.get('thinking', 'N/A')}")
        print(f"\n📢 Plan explicado:")
        print(f"   {user_msg.get('plan', 'N/A')}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

async def ejemplo_consulta_compleja():
    """
    Ejemplo con una consulta compleja que podría requerir múltiples pasos.
    """
    print("\n🧠 Ejemplo: Consulta Compleja")
    print("=" * 50)
    
    user_query = "Analiza mis notas sobre IA de la última semana y busca conexiones con mis proyectos actuales"
    context = "Conversación previa sobre proyectos de IA y análisis de datos"
    
    print(f"👤 Usuario: {user_query}")
    print(f"📝 Contexto: {context}")
    
    try:
        plan = await create_execution_plan(user_query, context)
        
        print(f"\n🧠 Análisis del agente:")
        analysis = plan.get("query_analysis", {})
        print(f"   Tipo: {analysis.get('type', 'unknown')}")
        print(f"   Complejidad: {analysis.get('complexity', 0)}/5")
        print(f"   Requiere herramientas: {analysis.get('requires_tools', False)}")
        
        strategy = plan.get("execution_strategy", {})
        print(f"\n📋 Estrategia:")
        print(f"   Enfoque: {strategy.get('approach', 'N/A')}")
        print(f"   Herramienta principal: {strategy.get('primary_tool', 'N/A')}")
        print(f"   Razonamiento: {strategy.get('reasoning', 'N/A')}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

async def ejemplo_consulta_ambigua():
    """
    Ejemplo con una consulta ambigua que necesita interpretación.
    """
    print("\n🧠 Ejemplo: Consulta Ambigua")
    print("=" * 50)
    
    user_query = "Busca eso que hablamos ayer sobre el proyecto"
    context = "Conversación previa sobre múltiples proyectos y temas"
    
    print(f"👤 Usuario: {user_query}")
    print(f"📝 Contexto: {context}")
    
    try:
        plan = await create_execution_plan(user_query, context)
        
        print(f"\n🧠 Análisis del agente:")
        analysis = plan.get("query_analysis", {})
        print(f"   Tipo: {analysis.get('type', 'unknown')}")
        print(f"   Complejidad: {analysis.get('complexity', 0)}/5")
        
        strategy = plan.get("execution_strategy", {})
        print(f"\n📋 Estrategia para consulta ambigua:")
        print(f"   Herramienta: {strategy.get('primary_tool', 'N/A')}")
        print(f"   Razonamiento: {strategy.get('reasoning', 'N/A')}")
        
        user_msg = plan.get("user_message", {})
        print(f"\n💭 Cómo maneja la ambigüedad:")
        print(f"   {user_msg.get('thinking', 'N/A')}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

def ejemplo_comparacion_antes_despues():
    """
    Muestra la diferencia entre el comportamiento anterior y el nuevo.
    """
    print("\n⚖️ Comparación: Antes vs Después")
    print("=" * 50)
    
    print("🔴 ANTES (Reactivo):")
    print("   1. Usuario: 'Busca documentos sobre IA'")
    print("   2. Agente: [Ve 'busca' → usa memory_search_optimized inmediatamente]")
    print("   3. Resultado: Búsqueda directa, posible herramienta subóptima")
    
    print("\n🟢 DESPUÉS (Con Planificación):")
    print("   1. Usuario: 'Busca documentos sobre IA'")
    print("   2. Agente: [PLANIFICA]")
    print("      - Analiza: consulta simple, búsqueda específica")
    print("      - Evalúa: memory_search_optimized vs natural_query_interpreter")
    print("      - Decide: memory_search_optimized es óptimo")
    print("      - Razona: 'Consulta directa con parámetros claros'")
    print("   3. Resultado: Herramienta óptima seleccionada conscientemente")
    
    print("\n✨ BENEFICIOS:")
    print("   • Mejor selección de herramientas")
    print("   • Manejo inteligente de ambigüedad")
    print("   • Transparencia en el proceso de decisión")
    print("   • Capacidad de estrategias multi-paso (futuro)")

async def ejemplo_casos_especiales():
    """
    Ejemplos de casos especiales donde la planificación es más valiosa.
    """
    print("\n🎯 Casos Especiales donde la Planificación Brilla")
    print("=" * 50)
    
    casos = [
        {
            "consulta": "Necesito información sobre el proyecto X pero no recuerdo si está en mis notas o documentos",
            "valor": "Planifica búsqueda en múltiples fuentes"
        },
        {
            "consulta": "Analiza todo lo que tengo sobre machine learning y crea un resumen",
            "valor": "Identifica que necesita análisis profundo, no búsqueda simple"
        },
        {
            "consulta": "¿Qué pasó en la reunión de ayer?",
            "valor": "Reconoce ambigüedad temporal y planifica búsqueda contextual"
        },
        {
            "consulta": "Guarda esta información importante para el futuro",
            "valor": "Identifica intención de almacenamiento vs búsqueda"
        }
    ]
    
    for i, caso in enumerate(casos, 1):
        print(f"\n{i}. 💬 '{caso['consulta']}'")
        print(f"   🎯 Valor de planificación: {caso['valor']}")

async def main():
    """
    Ejecuta todos los ejemplos de planificación.
    """
    print("🧠 Ejemplos del Sistema de Planificación del Agente")
    print("=" * 60)
    
    try:
        await ejemplo_consulta_simple()
        await ejemplo_consulta_compleja()
        await ejemplo_consulta_ambigua()
        ejemplo_comparacion_antes_despues()
        await ejemplo_casos_especiales()
        
        print("\n" + "=" * 60)
        print("✅ Ejemplos de planificación completados!")
        
        print("\n🚀 PRÓXIMOS PASOS:")
        print("   • La planificación está integrada en el flujo del agente")
        print("   • Se ejecuta automáticamente antes de seleccionar herramientas")
        print("   • Mejora la precisión y transparencia del agente")
        print("   • Base para futuras capacidades multi-paso")
        
    except Exception as e:
        print(f"\n❌ Error en los ejemplos: {e}")
        logger.error("Error ejecutando ejemplos", exc_info=True)

if __name__ == "__main__":
    # Ejecutar ejemplos
    asyncio.run(main())
