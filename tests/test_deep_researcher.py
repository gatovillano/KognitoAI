import asyncio
import sys
import os
import uuid

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock settings if needed or ensure environment is loaded
from dotenv import load_dotenv
load_dotenv()

from core.agents.deep_researcher import compile_deep_researcher_graph
from core.config import settings

# Mock get_tool_by_name to avoid full dependency injection if possible, 
# or ensure we have a valid account_id.
# For this test, we'll try to use the real tools if credentials are present.

async def main():
    print("--- Iniciando Test de Deep Researcher ---")
    
    # Initialize LLMs first
    print("Inicializando LLMs...")
    from core.llm_manager import initialize_llms
    await initialize_llms()
    print("✅ LLMs inicializados")
    
    # Use a dummy UUID for testing if no real user is available
    # In a real scenario, we might need a valid account ID from the DB
    account_id = str(uuid.uuid4())
    
    print(f"Usando Account ID temporal: {account_id}")
    
    # Compile the graph
    try:
        graph = compile_deep_researcher_graph()
    except Exception as e:
        print(f"Error compilando el grafo: {e}")
        return
    
    # Define initial state
    query = "Cual es el estado de la computacion cuantica en 2025?"
    if len(sys.argv) > 1:
        query = sys.argv[1]
        
    initial_state = {
        "query": query,
        "account_id": account_id,
        "research_plan": [],
        "findings": [],
        "iterations": 0,
        "messages": []
    }
    
    print(f"Consulta: {query}")
    print("Ejecutando grafo...")
    
    try:
        # Run the graph
        async for output in graph.astream(initial_state):
            for key, value in output.items():
                print(f"\n--- Nodo finalizado: {key} ---")
                if key == "scope":
                    print("Plan:", value.get("research_plan"))
                elif key == "research":
                    print(f"Iteración: {value.get('iterations')}")
                    findings = value.get("findings", [])
                    if findings:
                        print(f"Nuevos hallazgos: {len(findings)}")
                        # Print first 100 chars of the last finding
                        last_finding = findings[-1]
                        content = last_finding.get('content', '')
                        print(f"Último hallazgo ({last_finding.get('source')}): {content[:100]}...")
                elif key == "synthesize":
                    print("\nReporte Final:")
                    print("="*50)
                    print(value.get("final_report"))
                    print("="*50)
    except Exception as e:
        print(f"Error durante la ejecución: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
