#!/usr/bin/env python3
"""
Ejemplo de uso del Sistema de Planificación del Agente

Este script demuestra cómo funciona el nuevo sistema de planificación
implementado en core/agent.py según la especificación de docs/agent_planning_system.md
"""

import asyncio
import json
import logging
from typing import Dict, Any, List

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Simulación de herramientas para testing
class MockTool:
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    def __repr__(self):
        return f"MockTool(name='{self.name}', description='{self.description}')"

# Importar las funciones de planificación (simuladas para el ejemplo)
def _create_basic_plan(user_query: str) -> dict:
    """Plan de fallback seguro para el sistema de planificación."""
    logger.info(f"🛡️ Usando plan de fallback seguro para: '{user_query[:50]}...'")
    
    return {
        "query_analysis": {
            "type": "simple",
            "complexity": 2,
            "intent": "Consulta general que requiere interpretación natural",
            "requires_tools": True
        },
        "execution_strategy": {
            "approach": "Interpretación natural conservadora",
            "primary_tool": "natural_query_interpreter",
            "fallback_tool": "memory_search_optimized",
            "parameters": {"query": user_query},
            "reasoning": "Plan de fallback seguro - usar interpretación natural para consultas generales"
        },
        "user_message": {
            "thinking": "Análisis pendiente - usando estrategia conservadora",
            "plan": "Interpretaré tu consulta de forma natural para determinar la mejor acción"
        }
    }

async def create_execution_plan(user_query: str, tools: List[Any], context: str = "") -> dict:
    """
    Crea un plan de ejecución inteligente para la consulta del usuario.
    
    Esta función añade una fase de "pensamiento" al agente antes de ejecutar herramientas,
    mejorando significativamente la selección de herramientas y la calidad de las respuestas.
    """
    logger.info(f"🧠 Creando plan de ejecución para: '{user_query[:50]}...'")
    
    # Para el ejemplo, simulamos el análisis
    # En la implementación real, esto usaría un LLM
    
    # Construir lista de herramientas disponibles para el prompt
    available_tools = []
    for tool in tools:
        tool_info = {
            "name": getattr(tool, 'name', 'unknown'),
            "description": getattr(tool, 'description', 'Sin descripción')
        }
        available_tools.append(tool_info)
    
    # Análisis simple basado en palabras clave (simulado)
    user_query_lower = user_query.lower()
    
    # Determinar tipo de consulta
    if any(word in user_query_lower for word in ["busca", "encuentra", "search"]):
        query_type = "simple"
        complexity = 2
        primary_tool = "memory_search_optimized"
        reasoning = "Consulta de búsqueda directa con parámetros claros"
    elif any(word in user_query_lower for word in ["analiza", "explícame", "cómo", "por qué"]):
        query_type = "complex"
        complexity = 4
        primary_tool = "knowledge_graph"
        reasoning = "Requiere análisis profundo y detección de patrones"
    elif any(word in user_query_lower for word in ["eso", "ayer", "antes", "algo"]):
        query_type = "ambiguous"
        complexity = 3
        primary_tool = "natural_query_interpreter"
        reasoning = "Consulta vaga que necesita interpretación contextual"
    else:
        query_type = "simple"
        complexity = 2
        primary_tool = "natural_query_interpreter"
        reasoning = "Consulta general que requiere interpretación natural"
    
    # Construir plan
    execution_plan = {
        "query_analysis": {
            "type": query_type,
            "complexity": complexity,
            "intent": f"Análisis de consulta: {user_query[:100]}...",
            "requires_tools": True
        },
        "execution_strategy": {
            "approach": f"Enfoque basado en análisis de palabras clave",
            "primary_tool": primary_tool,
            "fallback_tool": "natural_query_interpreter",
            "parameters": {"query": user_query},
            "reasoning": reasoning
        },
        "user_message": {
            "thinking": f"Analizando consulta de tipo '{query_type}' con complejidad {complexity}/5",
            "plan": f"Planificado usar '{primary_tool}' para resolver tu consulta de forma óptima"
        }
    }
    
    logger.info(f"✅ Plan de ejecución creado exitosamente: {primary_tool}")
    return execution_plan

def format_plan_display(execution_plan: Dict[str, Any]) -> str:
    """Formatea el plan para mostrarlo de forma legible."""
    if not execution_plan:
        return "❌ No hay plan de ejecución disponible"
    
    plan_info = execution_plan.get("execution_strategy", {})
    thinking = execution_plan.get("user_message", {}).get("thinking", "")
    plan_description = execution_plan.get("user_message", {}).get("plan", "")
    
    return f"""
🧠 **PLAN DE EJECUCIÓN SUGERIDO:**
- Herramienta recomendada: {plan_info.get("primary_tool", "No especificada")}
- Enfoque: {plan_info.get("approach", "No especificado")}
- Razonamiento: {plan_info.get("reasoning", "No disponible")}

💭 **Pensamiento del Planificador:**
{thinking}

📋 **Plan para el Usuario:**
{plan_description}
"""

async def test_agent_planning():
    """Función principal de testing del sistema de planificación."""
    
    print("🚀 EJEMPLO DE SISTEMA DE PLANIFICACIÓN DEL AGENTE")
    print("=" * 60)
    
    # Definir herramientas mock
    tools = [
        MockTool("memory_search_optimized", "Búsqueda optimizada en memoria vectorial"),
        MockTool("natural_query_interpreter", "Interpretador de consultas en lenguaje natural"),
        MockTool("knowledge_graph", "Consulta al grafo de conocimiento"),
        MockTool("web_search", "Búsqueda en web externa"),
        MockTool("deep_research", "Investigación profunda multi-paso")
    ]
    
    # Casos de prueba basados en el documento
    test_cases = [
        {
            "name": "Consulta Simple",
            "query": "¿Qué documentos tengo sobre machine learning?",
            "context": "Workspace: ML-Research, Thread: docs-ml"
        },
        {
            "name": "Consulta Compleja", 
            "query": "Analiza mis notas sobre IA y busca conexiones con proyectos",
            "context": "Workspace: AI-Analysis, Thread: notes-review"
        },
        {
            "name": "Consulta Ambigua",
            "query": "Busca eso que hablamos ayer",
            "context": "Workspace: General, Thread: chat-history"
        },
        {
            "name": "Consulta Multi-Dominio",
            "query": "Explícame cómo se relacionan mis proyectos de investigación con las tendencias actuales",
            "context": "Workspace: Research, Thread: trends-analysis"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 CASO DE PRUEBA {i}: {test_case['name']}")
        print("-" * 50)
        print(f"👤 Consulta: {test_case['query']}")
        print(f"🏢 Contexto: {test_case['context']}")
        print()
        
        # Crear plan de ejecución
        try:
            execution_plan = await create_execution_plan(
                user_query=test_case['query'],
                tools=tools,
                context=test_case['context']
            )
            
            # Mostrar plan formateado
            print(format_plan_display(execution_plan))
            
        except Exception as e:
            logger.error(f"❌ Error en planificación: {e}")
            # Usar plan de fallback
            execution_plan = _create_basic_plan(test_case['query'])
            print("🛡️ USANDO PLAN DE FALLBACK:")
            print(format_plan_display(execution_plan))
        
        print("\n" + "="*60)
    
    print("\n✅ DEMOSTRACIÓN COMPLETADA")
    print("\n🎯 BENEFICIOS DEL SISTEMA:")
    print("• Mejor selección de herramientas (~70% → ~90% precisión)")
    print("• Manejo inteligente de consultas ambiguas")
    print("• Proceso transparente y explicable")
    print("• Preparación para estrategias multi-paso")
    print("• Fallback seguro en caso de errores")

if __name__ == "__main__":
    asyncio.run(test_agent_planning())
