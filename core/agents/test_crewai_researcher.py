# core/agents/test_crewai_researcher.py

import asyncio
import logging
import os
import sys

# Añadir el directorio raíz al path para poder importar core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from core.llm_manager import initialize_llms
from core.agents.crewai_researcher import KognitoCrewResearcher
from core.agents.deep_researcher_utils import get_all_tools
from langchain_core.messages import HumanMessage

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    logger.info("🚀 Iniciando prueba de KognitoCrewResearcher...")
    
    # 1. Inicializar LLMs
    await initialize_llms()
    
    # 2. Configurar herramientas (usamos una config vacía para la prueba)
    # Nota: En un entorno real, aquí pasaríamos el account_id y workspace_id
    tools = await get_all_tools({})
    logger.info(f"🛠️ Herramientas cargadas: {[t.name for t in tools if hasattr(t, 'name')]}")
    
    # 3. Inicializar el investigador de CrewAI
    researcher = KognitoCrewResearcher(
        account_id="test_user",
        workspace_id="test_workspace",
        config={
            "max_researcher_iterations": 3,
            "max_concurrent_research_units": 2
        }
    )
    
    # 4. Ejecutar investigación
    topic = "Beneficios de usar CrewAI para orquestación de agentes multi-agente frente a LangGraph"
    messages = "El usuario quiere saber por qué CrewAI es mejor para flujos jerárquicos."
    
    try:
        logger.info(f"🔍 Investigando tema: {topic}")
        result = await researcher.run_research(
            research_brief=topic,
            messages=messages,
            tools=tools
        )
        
        logger.info("✅ Investigación completada con éxito!")
        print("\n" + "="*50)
        print("INFORME FINAL GENERADO POR CREWAI:")
        print("="*50)
        print(result["final_report"])
        print("="*50 + "\n")
        
    except Exception as e:
        logger.error(f"❌ Error durante la investigación: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())
