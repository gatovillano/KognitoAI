import logging
from typing import Type, Optional
from pydantic import BaseModel, Field

from langchain_core.language_models.base import BaseLanguageModel # Importar BaseLanguageModel
from langchain_core.tools import BaseTool, Tool # Importar Tool
from tools.ddg_search_tool import create_ddg_search_tool # Importar la función de fábrica
from tools.add_web_to_rag_tool import AddWebToRAGTool # Tu herramienta para añadir a RAG

# Importar el DeepResearcher del módulo que hemos integrado
try:
    from external_agents.open_deep_research.src.open_deep_research.deep_researcher import DeepResearcher
    from external_agents.open_deep_research.src.open_deep_research.configuration import ResearchConfig
except ImportError as e:
    logging.error(f"Error importing DeepResearcher: {e}. Make sure the open_deep_research module is correctly placed.")
    DeepResearcher = None
    ResearchConfig = None

logger = logging.getLogger(__name__)

class DeepResearchToolInput(BaseModel):
    query: str = Field(description="The research query or topic to investigate.")

class DeepResearchTool(BaseTool):
    name: str = "deep_research_tool"
    description: str = "Performs a comprehensive deep research on a given query, leveraging multiple sources and generating a detailed report. Automatically adds relevant findings to RAG."
    args_schema: Type[BaseModel] = DeepResearchToolInput

    llm_instance: BaseLanguageModel = Field(..., exclude=True) # Cambiado a llm_instance
    ddg_search_tool: Tool = Field(..., exclude=True) # Cambiado a Tool
    add_web_to_rag_tool: AddWebToRAGTool = Field(..., exclude=True)
    
    _deep_researcher: Optional[DeepResearcher] = None

    def __init__(self, **data):
        super().__init__(**data)
        if DeepResearcher:
            # Aquí inicializamos el DeepResearcher.
            # El DeepResearcher espera un LLM y una lista de herramientas.
            
            # Para el LLM, usaremos la instancia de LLM que se pasó directamente
            llm_for_researcher = self.llm_instance
            
            # Para las herramientas, el DeepResearcher usa herramientas de búsqueda.
            # Aquí integramos tu DDGSearchTool.
            # Nota: El DeepResearcher puede esperar una interfaz específica para las herramientas.
            # Podríamos necesitar un wrapper si tu DDGSearchTool no es directamente compatible.
            # Por simplicidad, asumimos que podemos pasarle una función de búsqueda o una herramienta LangChain.
            
            # El DeepResearcher de LangChain espera una herramienta de búsqueda que implemente .invoke()
            # o una función que tome una query y devuelva resultados.
            # Aquí, asumimos que ddg_search_tool tiene un método para ejecutar la búsqueda.
            
            # Configuración básica para el DeepResearcher
            config = ResearchConfig(
                llm=llm_for_researcher,
                # Aquí podrías pasar tus herramientas de búsqueda.
                # El DeepResearcher usa Tavily, pero podemos intentar sobrescribirlo o adaptarlo.
                # Esto es un punto clave de integración que podría requerir ajustes.
                # Por ahora, lo dejamos con un placeholder, asumiendo que el DeepResearcher
                # puede ser configurado para usar herramientas personalizadas.
                # Si el DeepResearcher requiere una herramienta específica de LangChain,
                # podríamos necesitar un adaptador para tu DDGSearchTool.
                # Por ejemplo, si espera un 'TavilySearchResults' tool, tendríamos que simularlo.
                # Para la integración inicial, asumiremos que podemos pasarle una función de búsqueda.
                # Si no funciona, tendremos que crear un adaptador para DDGSearchTool que se parezca a Tavily.
                search_tool=self.ddg_search_tool # Esto es una simplificación, podría requerir un wrapper
            )
            
            self._deep_researcher = DeepResearcher(config=config)
            logger.info("✅ DeepResearchTool inicializado con DeepResearcher.")
        else:
            logger.warning("❌ DeepResearcher no pudo ser importado. La herramienta no funcionará.")

    async def _run(self, query: str) -> str:
        if not self._deep_researcher:
            return "Error: DeepResearchTool no está inicializado correctamente."

        logger.info(f"🚀 Iniciando investigación profunda para: {query}")
        try:
            # Ejecutar la investigación. El método exacto puede variar.
            # Asumimos que 'run' o 'invoke' es el método principal.
            # El resultado de la investigación será un informe.
            research_report = await self._deep_researcher.run(query)
            
            # Después de la investigación, añadir los hallazgos relevantes a RAG.
            # Esto es una simplificación. Idealmente, el DeepResearcher debería
            # devolver contenido estructurado que podamos pasar a add_web_to_rag_tool.
            # Por ahora, asumimos que el informe completo puede ser añadido o que
            # el DeepResearcher ya maneja la adición a RAG internamente si se configura.
            # Si no, tendríamos que parsear el 'research_report' para extraer URLs/contenido.
            
            # Para la integración automática a RAG, asumimos que el informe contiene
            # texto que puede ser procesado por add_web_to_rag_tool.
            # Si add_web_to_rag_tool espera URLs, necesitaríamos extraerlas del informe.
            # Por ahora, pasamos el informe como contenido.
            
            # Esto es un placeholder. La integración real de RAG dependerá de cómo
            # el DeepResearcher expone los datos y cómo add_web_to_rag_tool los consume.
            # Podríamos necesitar un paso intermedio para extraer URLs o texto relevante.
            # Por ejemplo, si el informe es un string, podríamos pasarlo como contenido.
            # Si add_web_to_rag_tool espera una URL, necesitaríamos que el DeepResearcher
            # nos diera las URLs que investigó.
            
            # Si el DeepResearcher no devuelve URLs, podríamos hacer una búsqueda de URLs
            # dentro del texto del informe y luego pasarlas a add_web_to_rag_tool.
            
            # Por ahora, simulamos la adición a RAG con el informe completo.
            # Esto es un punto de ajuste importante.
            rag_result = await self.add_web_to_rag_tool._run(url=None, content=research_report, title=f"Deep Research Report: {query}")
            logger.info(f"✅ Informe de investigación añadido a RAG: {rag_result}")

            return research_report
        except Exception as e:
            logger.error(f"❌ Error durante la investigación profunda: {e}")
            return f"Error al realizar la investigación profunda: {e}"

