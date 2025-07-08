# examples/add_web_to_rag_example.py

"""
Ejemplo de uso de la herramienta AddWebToRAGTool.
Demuestra cómo añadir contenido web directamente a la base de conocimiento.
"""

import asyncio
import logging
from tools.add_web_to_rag_tool import AddWebToRAGTool

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def ejemplo_basico():
    """
    Ejemplo básico de uso de AddWebToRAGTool.
    """
    print("🌐 Ejemplo básico de AddWebToRAGTool")
    print("=" * 50)
    
    # Crear instancia de la herramienta
    tool = AddWebToRAGTool()
    
    # Parámetros del ejemplo
    parametros = {
        "url": "https://python.langchain.com/docs/how_to/MultiQueryRetriever/",
        "topic": "langchain_docs",
        "account_id": "usuario_ejemplo",
        "custom_title": "MultiQueryRetriever Documentation"
    }
    
    print(f"📋 Parámetros:")
    for key, value in parametros.items():
        print(f"   {key}: {value}")
    
    try:
        # Ejecutar la herramienta
        resultado = await tool._arun(**parametros)
        print(f"\n✅ Resultado:")
        print(resultado)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")

async def ejemplo_con_workspace():
    """
    Ejemplo añadiendo contenido a un workspace específico.
    """
    print("\n🏢 Ejemplo con workspace específico")
    print("=" * 50)
    
    tool = AddWebToRAGTool()
    
    parametros = {
        "url": "https://docs.python.org/3/tutorial/",
        "topic": "python_tutorial",
        "account_id": "usuario_ejemplo",
        "workspace_id": "workspace_dev",
        "custom_title": "Python Official Tutorial"
    }
    
    print(f"📋 Parámetros:")
    for key, value in parametros.items():
        print(f"   {key}: {value}")
    
    try:
        resultado = await tool._arun(**parametros)
        print(f"\n✅ Resultado:")
        print(resultado)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")

async def ejemplo_multiples_urls():
    """
    Ejemplo añadiendo múltiples URLs relacionadas.
    """
    print("\n📚 Ejemplo con múltiples URLs")
    print("=" * 50)
    
    tool = AddWebToRAGTool()
    
    urls_ia = [
        {
            "url": "https://openai.com/blog/chatgpt",
            "topic": "inteligencia_artificial",
            "custom_title": "ChatGPT Introduction"
        },
        {
            "url": "https://www.anthropic.com/claude",
            "topic": "inteligencia_artificial", 
            "custom_title": "Claude AI Assistant"
        }
    ]
    
    account_id = "usuario_ejemplo"
    workspace_id = "workspace_ia"
    
    for i, url_info in enumerate(urls_ia, 1):
        print(f"\n📄 Procesando URL {i}/{len(urls_ia)}: {url_info['custom_title']}")
        
        try:
            resultado = await tool._arun(
                url=url_info["url"],
                topic=url_info["topic"],
                account_id=account_id,
                workspace_id=workspace_id,
                custom_title=url_info["custom_title"]
            )
            print(f"✅ {url_info['custom_title']}: Procesado exitosamente")
            
        except Exception as e:
            print(f"❌ Error procesando {url_info['custom_title']}: {e}")

def ejemplo_uso_desde_agente():
    """
    Ejemplo de cómo el agente usaría esta herramienta.
    """
    print("\n🤖 Ejemplo de uso desde el agente")
    print("=" * 50)
    
    print("💬 Usuario: 'Guarda este artículo sobre machine learning en mi base de conocimiento'")
    print("🔗 URL proporcionada: https://scikit-learn.org/stable/tutorial/basic/tutorial.html")
    
    print("\n🧠 El agente detectaría:")
    print("   • Intención: Guardar contenido web")
    print("   • Herramienta a usar: add_web_to_rag")
    print("   • Parámetros necesarios:")
    print("     - url: https://scikit-learn.org/stable/tutorial/basic/tutorial.html")
    print("     - topic: machine_learning (inferido del contexto)")
    print("     - account_id: [del contexto del usuario]")
    print("     - custom_title: 'Scikit-learn Tutorial' (opcional)")
    
    print("\n⚡ Ejecución automática:")
    print("   1. Extrae contenido de la URL")
    print("   2. Procesa y divide en chunks")
    print("   3. Almacena en base vectorial")
    print("   4. Confirma al usuario")

async def ejemplo_casos_de_uso():
    """
    Muestra diferentes casos de uso de la herramienta.
    """
    print("\n🎯 Casos de uso comunes")
    print("=" * 50)
    
    casos_uso = [
        {
            "descripcion": "📖 Documentación técnica",
            "ejemplo": "Guardar docs de APIs, frameworks, librerías",
            "url_ejemplo": "https://fastapi.tiangolo.com/tutorial/"
        },
        {
            "descripcion": "📰 Artículos de investigación",
            "ejemplo": "Papers, blogs técnicos, análisis de mercado",
            "url_ejemplo": "https://arxiv.org/abs/2103.00020"
        },
        {
            "descripcion": "📚 Recursos educativos",
            "ejemplo": "Tutoriales, guías, cursos online",
            "url_ejemplo": "https://www.coursera.org/learn/machine-learning"
        },
        {
            "descripcion": "🏢 Contenido empresarial",
            "ejemplo": "Políticas, procedimientos, wikis internos",
            "url_ejemplo": "https://company-wiki.internal/procedures"
        },
        {
            "descripcion": "🔬 Referencias técnicas",
            "ejemplo": "Especificaciones, RFCs, estándares",
            "url_ejemplo": "https://tools.ietf.org/html/rfc7519"
        }
    ]
    
    for caso in casos_uso:
        print(f"\n{caso['descripcion']}")
        print(f"   Uso: {caso['ejemplo']}")
        print(f"   Ejemplo: {caso['url_ejemplo']}")

async def main():
    """
    Ejecuta todos los ejemplos.
    """
    print("🌐 Ejemplos de AddWebToRAGTool")
    print("=" * 60)
    
    try:
        await ejemplo_basico()
        await ejemplo_con_workspace()
        await ejemplo_multiples_urls()
        ejemplo_uso_desde_agente()
        await ejemplo_casos_de_uso()
        
        print("\n" + "=" * 60)
        print("✅ Todos los ejemplos completados!")
        print("\n💡 Consejos:")
        print("   • La herramienta maneja automáticamente timeouts y errores")
        print("   • Extrae títulos automáticamente o permite títulos personalizados")
        print("   • Soporta workspaces para organización avanzada")
        print("   • Procesa contenido en chunks optimizados para búsqueda")
        
    except Exception as e:
        print(f"\n❌ Error en los ejemplos: {e}")
        logger.error("Error ejecutando ejemplos", exc_info=True)

if __name__ == "__main__":
    # Ejecutar ejemplos
    asyncio.run(main())
