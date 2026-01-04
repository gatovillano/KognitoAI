# core/agents/crewai_researcher.py

import logging
import re
from typing import List, Dict, Any, Optional
from crewai import Agent, Task, Crew, Process
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from core.llm_manager import get_main_llm, get_fast_llm, initialize_llms
from core.agents.deep_researcher_prompts import (
    lead_researcher_prompt,
    research_system_prompt,
    compress_research_system_prompt,
    final_report_generation_prompt
)
from core.utils.date_utils import get_today_str

logger = logging.getLogger(__name__)

class KognitoCrewResearcher:
    def __init__(self, account_id: Optional[str] = None, workspace_id: Optional[str] = None, config: Dict[str, Any] = None):
        self.account_id = account_id
        self.workspace_id = workspace_id
        self.config = config or {}
        self.main_llm = get_main_llm()
        self.fast_llm = get_fast_llm()
        self.today = get_today_str()

    async def _get_tools(self, provided_tools: Optional[List[Any]] = None) -> List[Any]:
        """Obtiene las herramientas necesarias, priorizando las proporcionadas."""
        if provided_tools:
            return provided_tools
        
        # Si no hay herramientas, cargamos las de Kognito por defecto
        from langchain_core.runnables import RunnableConfig
        from core.agents.deep_researcher_utils import get_all_tools
        from crewai.tools import BaseTool as CrewBaseTool
        from pydantic import Field

        run_config = RunnableConfig(configurable={
            "account_id": self.account_id,
            "workspace_id": self.workspace_id
        })
        
        langchain_tools = await get_all_tools(run_config)
        
        # Clase adaptadora interna para herramientas de LangChain que fallan en la conversión automática
        class CrewAILangChainAdapter(CrewBaseTool):
            name: str = Field(..., description="Name of the tool")
            description: str = Field(..., description="Description of the tool")
            langchain_tool: Any = Field(..., description="The original LangChain tool")
            
            def __init__(self, **data):
                super().__init__(**data)
                # Intentar heredar el esquema de argumentos si existe
                if hasattr(self.langchain_tool, 'args_schema'):
                    self.args_schema = self.langchain_tool.args_schema

            def _run(self, *args, **kwargs):
                """Execute the tool."""
                import asyncio
                import nest_asyncio
                
                def run_sync_or_async(func, *f_args, **f_kwargs):
                    if asyncio.iscoroutinefunction(func):
                        try:
                            loop = asyncio.get_event_loop()
                        except RuntimeError:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                        
                        if loop.is_running():
                            nest_asyncio.apply()
                            return loop.run_until_complete(func(*f_args, **f_kwargs))
                        else:
                            return loop.run_until_complete(func(*f_args, **f_kwargs))
                    else:
                        return func(*f_args, **f_kwargs)

                try:
                    # Caso 1: La herramienta tiene un método _run (síncrono) o _arun (asíncrono)
                    if not hasattr(self.langchain_tool, 'func'):
                         # Usamos el método run de LangChain que ya gestiona la lógica de despacho
                         tool_input = kwargs if kwargs else args[0] if args else {}
                         
                         if hasattr(self.langchain_tool, '_arun'):
                             # Si tiene _arun, es probable que prefiera ejecución asíncrona
                             return run_sync_or_async(self.langchain_tool._arun, **(tool_input if isinstance(tool_input, dict) else {"tool_input": tool_input}))
                         
                         return self.langchain_tool.run(tool_input)
                    
                    # Caso 2: Es una herramienta funcional (Tool)
                    if hasattr(self.langchain_tool, 'func') and self.langchain_tool.func:
                        return run_sync_or_async(self.langchain_tool.func, *args, **kwargs)

                    # Caso 3: Fallback genérico
                    return self.langchain_tool.run(kwargs if kwargs else args[0] if args else {})
                except Exception as e:
                    logger.error(f"Error ejecutando herramienta {self.name} vía adaptador: {e}", exc_info=True)
                    return f"Error ejecutando herramienta {self.name}: {str(e)}"

        # Convertir herramientas de LangChain a CrewAI
        crewai_tools = []
        for tool in langchain_tools:
            try:
                # Intentar usar el método oficial de conversión primero
                if hasattr(CrewBaseTool, 'from_langchain'):
                    crew_tool = CrewBaseTool.from_langchain(tool)
                    crewai_tools.append(crew_tool)
                else:
                    raise AttributeError("from_langchain not found")
            except Exception as e:
                logger.warning(f"Conversión automática falló para {tool.name} ({e}). Usando adaptador robusto.")
                # Usar nuestro adaptador manual
                try:
                    adapter = CrewAILangChainAdapter(
                        name=tool.name,
                        description=tool.description,
                        langchain_tool=tool
                    )
                    crewai_tools.append(adapter)
                except Exception as adapter_error:
                    logger.error(f"Error fatal adaptando herramienta {tool.name}: {adapter_error}")
                    # Si todo falla, intentamos pasarla raw, aunque probablemente falle la validación
                    crewai_tools.append(tool)
                
        return crewai_tools

    def create_agents(self, tools: List[Any]) -> List[Agent]:
        """Crea los agentes de la Crew con configuraciones optimizadas."""
        
        # 1. Manager: Orquestador
        manager_agent = Agent(
            role='Director de Investigación de Élite',
            goal='Orquestar una investigación de alta complejidad, asegurando profundidad y rigor.',
            backstory=lead_researcher_prompt.format(
                date=self.today,
                max_researcher_iterations=self.config.get('max_researcher_iterations', 10),
                max_concurrent_research_units=self.config.get('max_concurrent_research_units', 3)
            ),
            llm=self.main_llm,
            allow_delegation=True,
            verbose=True
        )

        # 2. Investigador: Ejecutor de búsquedas
        researcher_agent = Agent(
            role='Investigador Especialista de Alto Nivel',
            goal='Agotar todas las fuentes posibles para proporcionar una respuesta definitiva.',
            backstory=research_system_prompt.format(
                date=self.today,
                mcp_prompt="" 
            ),
            tools=tools,
            llm=self.fast_llm,
            allow_delegation=False,
            verbose=True
        )

        # 3. Analista: Estructurador de datos
        analyst_agent = Agent(
            role='Analista de Datos y Organizador',
            goal='Estructurar y preservar cada fragmento de información recolectado.',
            backstory=compress_research_system_prompt.format(date=self.today),
            llm=self.fast_llm,
            allow_delegation=False,
            verbose=True
        )

        # 4. Redactor: Generador del informe final
        # Nota: No formateamos research_brief, messages y findings aquí porque se pasan en la tarea
        writer_agent = Agent(
            role='Redactor Técnico de Élite',
            goal='Generar una tesina de investigación exhaustiva y erudita.',
            backstory=final_report_generation_prompt.replace("{research_brief}", "el tema solicitado")
                                                   .replace("{messages}", "el contexto del usuario")
                                                   .replace("{findings}", "los hallazgos de la investigación")
                                                   .format(date=self.today),
            llm=self.main_llm,
            allow_delegation=False,
            verbose=True
        )

        return [manager_agent, researcher_agent, analyst_agent, writer_agent]

    async def run_research(self, research_brief: str, messages: str, tools: Optional[List[Any]] = None) -> Dict[str, Any]:
        """Ejecuta el proceso de investigación completo usando CrewAI."""
        
        # Asegurar que los LLMs estén inicializados
        if get_main_llm() is None:
            logger.info("🤖 LLMs no detectados. Inicializando...")
            await initialize_llms()
        
        # Actualizar referencias locales por si acaso
        self.main_llm = get_main_llm()
        self.fast_llm = get_fast_llm()
        
        actual_tools = await self._get_tools(tools)
        agents = self.create_agents(actual_tools)
        manager, researcher, analyst, writer = agents

        # Tarea 1: Investigación Exhaustiva
        task_research = Task(
            description=f"Realiza una investigación profunda sobre: {research_brief}. "
                        f"Busca datos técnicos, estadísticas y fuentes oficiales.",
            expected_output="Un inventario detallado de hallazgos con sus respectivas fuentes (URLs).",
            agent=researcher
        )

        # Tarea 2: Análisis y Estructuración
        task_analysis = Task(
            description="Toma los hallazgos de la investigación y estructúralos. "
                        "Preserva todas las URLs y datos cuantitativos.",
            expected_output="Un documento técnico organizado por fuentes.",
            agent=analyst,
            context=[task_research]
        )

        # Tarea 3: Redacción de la Tesina Final
        task_report = Task(
            description=f"Redacta la tesina final basada en los hallazgos. "
                        f"Contexto original: {messages}. "
                        f"Sigue estrictamente el formato de tesina: prosa narrativa, citas [N] y bibliografía final.",
            expected_output="La tesina de investigación final en formato Markdown.",
            agent=writer,
            context=[task_analysis]
        )

        # Configurar la Crew
        kognito_crew = Crew(
            agents=[researcher, analyst, writer], # Manager se excluye de esta lista
            tasks=[task_research, task_analysis, task_report],
            process=Process.hierarchical,
            manager_agent=manager,
            verbose=True
        )

        logger.info(f"🚀 Iniciando CrewAI para: {research_brief[:50]}...")
        
        try:
            result = await kognito_crew.kickoff_async()
            final_text = result.raw
            
            # Extracción de fuentes (URLs) del texto final
            sources = []
            urls = re.findall(r'https?://[^\s\)\],]+', final_text)
            unique_urls = list(set(urls))
            
            for i, url in enumerate(unique_urls, 1):
                sources.append({
                    "id": i,
                    "title": f"Fuente {i}",
                    "url": url,
                    "snippet": "Extraído del informe de investigación.",
                    "type": "web"
                })

            return {
                "final_report": final_text,
                "sources": sources,
                "recommendations": self._extract_recommendations(final_text)
            }
        except Exception as e:
            logger.error(f"❌ Error en la ejecución de CrewAI: {e}", exc_info=True)
            return {
                "final_report": f"Error durante la investigación: {str(e)}",
                "sources": [],
                "recommendations": []
            }

    def _extract_recommendations(self, text: str) -> List[str]:
        """Intenta extraer recomendaciones del texto final."""
        recommendations = []
        # Buscar secciones de recomendaciones o proyecciones
        parts = re.split(r'(?i)recomendaciones|proyecciones|implicaciones estratégicas', text)
        if len(parts) > 1:
            # Tomar la última parte y buscar párrafos que parezcan recomendaciones
            last_part = parts[-1]
            paragraphs = [p.strip() for p in last_part.split('\n\n') if len(p.strip()) > 50]
            recommendations = paragraphs[:5] # Tomar las primeras 5
        return recommendations

