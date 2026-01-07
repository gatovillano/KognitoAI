
import asyncio
import os
from dotenv import load_dotenv
from tools.tavily_search_tool import TavilySearchTool

async def test_tavily():
    # Cargar variables de entorno
    load_dotenv()
    
    print("🚀 Probando TavilySearchTool...")
    
    # Instanciar la herramienta
    tool = TavilySearchTool(account_id="test_user")
    
    # Realizar una búsqueda
    query = "Últimas noticias sobre inteligencia artificial 2024"
    print(f"🔍 Buscando: '{query}'...")
    
    try:
        result = await tool._arun(query=query)
        print("\n✅ Resultado obtenido:")
        print(f"Contexto para LLM (primeros 500 caracteres):\n{result['context_for_llm'][:500]}...")
        print(f"\nFuentes encontradas: {len(result['sources'])}")
        for source in result['sources'][:3]:
            print(f"- {source['title']}: {source['url']}")
            
    except Exception as e:
        print(f"\n❌ Error durante la prueba: {e}")

if __name__ == "__main__":
    asyncio.run(test_tavily())
