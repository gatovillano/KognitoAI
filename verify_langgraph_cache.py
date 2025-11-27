#!/usr/bin/env python3
"""
Script de verificación para el caché del grafo LangGraph.

Verifica que:
1. El grafo se compila solo una vez
2. Llamadas subsecuentes retornan la misma instancia
3. El grafo es funcional
"""

import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

def test_langgraph_caching():
    print("🧪 Verificando caché del grafo LangGraph...\n")
    
    try:
        # Import the function
        from core.agent import get_langgraph_agent, _compiled_agent_graph
        
        print("✅ Importación exitosa de get_langgraph_agent")
        
        # First call - should compile
        print("\n📝 Primera llamada a get_langgraph_agent()...")
        agent1 = get_langgraph_agent()
        print(f"   Tipo: {type(agent1)}")
        print(f"   ID de objeto: {id(agent1)}")
        
        # Second call - should return cached
        print("\n📝 Segunda llamada a get_langgraph_agent()...")
        agent2 = get_langgraph_agent()
        print(f"   Tipo: {type(agent2)}")
        print(f"   ID de objeto: {id(agent2)}")
        
        # Verify they are the same instance
        if agent1 is agent2:
            print("\n✅ ¡ÉXITO! Ambas llamadas retornan la misma instancia (cacheado correctamente)")
        else:
            print("\n❌ ERROR: Las llamadas retornan instancias diferentes (caché no funciona)")
            sys.exit(1)
        
        # Verify the graph is callable
        print("\n📝 Verificando que el grafo es invocable...")
        if hasattr(agent1, 'invoke') or hasattr(agent1, 'ainvoke'):
            print("✅ El grafo tiene métodos invoke/ainvoke")
        else:
            print("❌ El grafo no tiene métodos invoke/ainvoke")
            sys.exit(1)
        
        print("\n" + "="*60)
        print("🎉 TODAS LAS VERIFICACIONES PASARON")
        print("="*60)
        print("\n📊 Resumen:")
        print(f"   - Grafo compilado: ✅")
        print(f"   - Caché funcionando: ✅")
        print(f"   - Instancia única: ✅")
        print(f"   - Grafo invocable: ✅")
        
    except Exception as e:
        print(f"\n❌ Error durante la verificación: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    test_langgraph_caching()
