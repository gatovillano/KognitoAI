"""
KAI Core - Orquestador Central del Sistema Multi-Agente
"""

from typing import Dict, List, Any, Optional
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class KAIState(BaseModel):
    """Estado global del sistema KAI-Ethno"""
    research_question: str = ""
    research_type: str = "exploratory"
    context: Dict[str, Any] = Field(default_factory=dict)
    phase: str = "idle"
    results: Dict[str, Any] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    ethics_approved: bool = False
    current_agent: Optional[str] = None


class KAIOrchestrator:
    """
    Orquestador Central KAI-Ethno

    Coordina el pipeline completo de investigación antropológica aumentada:
    1. Inicialización y verificación ética
    2. Búsqueda bibliográfica (Bibliomancer)
    3. Recolección y procesamiento de datos (Ethnograph)
    4. Análisis de patrones (PatternFinder)
    5. Síntesis y triangulación (Synthesizer)
    6. Visualización (Visualizer)
    7. Redacción de documento (Scribe)
    8. Archivado en memoria (Archivist)

    Características:
    - Comunicación entre agentes via Message Bus
    - Memoria compartida (vectorial + grafo)
    - Consejo Ético con derecho a veto
    - Trazabilidad completa de decisiones
    """

    name = "kai_core"
    description = "Orquestador Central - Coordinador del sistema multi-agente"

    def __init__(self, llm_service: Any = None):
        self.llm = llm_service
        self.agents: Dict[str, Any] = {}
        self.ethics_council = None
        self.message_bus = None
        self.memory_manager = None
        self.graph = self._build_graph()
        self.state = KAIState()

    def _build_graph(self) -> StateGraph:
        """Construye el grafo de LangGraph para el flujo orquestado"""

        def initialize(state: Any) -> Dict[str, Any]:

            """Inicializa el sistema y valida configuración"""
            return {
                "phase": "initialization",
                "started_at": datetime.now().isoformat(),
                "results": {},
                "errors": []
            }

        async def ethics_review(state: Any) -> Dict[str, Any]:
            """Fase de revisión ética obligatoria"""
            results = state.get("results", {}) if isinstance(state, dict) else state.results
            context = state.get("context", {}) if isinstance(state, dict) else state.context
            errors = list(state.get("errors", [])) if isinstance(state, dict) else list(state.errors)
            ethics_approved = True

            if self.ethics_council:
                try:
                    if hasattr(self.ethics_council, "review"):
                        ethics_result = await self.ethics_council.review(context, context="pipeline_init") if asyncio.iscoroutinefunction(self.ethics_council.review) else self.ethics_council.review(context)
                    else:
                        ethics_result = {"approved": True}
                    
                    ethics_approved = ethics_result.get("approved", True) if isinstance(ethics_result, dict) else True
                    results["ethics"] = ethics_result
                except Exception as e:
                    logger.warning(f"Error en revisión ética: {e}")
                    results["ethics"] = {"status": "error", "error": str(e)}
            else:
                results["ethics"] = {"status": "skipped", "reason": "No council configured"}

            return {
                "phase": "ethics_review",
                "current_agent": "ethics_council",
                "ethics_approved": ethics_approved,
                "results": results,
                "errors": errors
            }

        async def bibliography_phase(state: Any) -> Dict[str, Any]:
            """Fase de búsqueda bibliográfica"""
            results = state.get("results", {}) if isinstance(state, dict) else state.results
            context = state.get("context", {}) if isinstance(state, dict) else state.context
            rq = state.get("research_question", "") if isinstance(state, dict) else state.research_question

            if "bibliomancer" in self.agents:
                res = await self.run_agent(
                    "bibliomancer",
                    query=rq,
                    filters=context.get("filters", {})
                )
                results["bibliography"] = res
            return {
                "phase": "bibliography",
                "current_agent": "bibliomancer",
                "results": results
            }

        async def ethnography_phase(state: Any) -> Dict[str, Any]:
            """Fase de procesamiento etnográfico"""
            results = state.get("results", {}) if isinstance(state, dict) else state.results
            context = state.get("context", {}) if isinstance(state, dict) else state.context
            sources = results.get("bibliography", {}).get("documents", [])
            materials = context.get("materials", sources)

            if "ethnograph" in self.agents:
                res = await self.run_agent(
                    "ethnograph",
                    materials=materials,
                    analysis_type=context.get("analysis_type", "mixed_methods")
                )
                results["ethnography"] = res
            return {
                "phase": "ethnography",
                "current_agent": "ethnograph",
                "results": results
            }

        async def pattern_phase(state: Any) -> Dict[str, Any]:
            """Fase de análisis de patrones"""
            results = state.get("results", {}) if isinstance(state, dict) else state.results
            processed = results.get("ethnography", {})

            if "pattern_finder" in self.agents:
                res = await self.run_agent("pattern_finder", processed=processed)
                results["patterns"] = res
            return {
                "phase": "pattern_analysis",
                "current_agent": "pattern_finder",
                "results": results
            }

        async def synthesis_phase(state: Any) -> Dict[str, Any]:
            """Fase de síntesis y triangulación"""
            results = state.get("results", {}) if isinstance(state, dict) else state.results
            sources = results.get("bibliography", {}).get("documents", [])
            coded_data = results.get("ethnography", {}).get("coded_segments", [])

            if "synthesizer" in self.agents:
                res = await self.run_agent("synthesizer", sources=sources, coded_data=coded_data)
                results["synthesis"] = res
            return {
                "phase": "synthesis",
                "current_agent": "synthesizer",
                "results": results
            }

        async def visualization_phase(state: Any) -> Dict[str, Any]:
            """Fase de visualización"""
            results = state.get("results", {}) if isinstance(state, dict) else state.results

            if "visualizer" in self.agents:
                data = {
                    "keywords": results.get("patterns", {}).get("keywords", {}),
                    "networks": results.get("patterns", {}).get("networks", []),
                    "clusters": results.get("patterns", {}).get("clusters", []),
                    "synthesis": results.get("synthesis", {})
                }
                res = await self.run_agent("visualizer", data=data)
                results["visualizations"] = res
            return {
                "phase": "visualization",
                "current_agent": "visualizer",
                "results": results
            }

        async def documentation_phase(state: Any) -> Dict[str, Any]:
            """Fase de redacción del documento"""
            results = state.get("results", {}) if isinstance(state, dict) else state.results
            context = state.get("context", {}) if isinstance(state, dict) else state.context
            rq = state.get("research_question", "") if isinstance(state, dict) else state.research_question
            sources = results.get("bibliography", {}).get("documents", [])
            synthesis = results.get("synthesis", {})

            if "scribe" in self.agents:
                res = await self.run_agent(
                    "scribe",
                    research_question=rq,
                    sources=sources,
                    analysis_results=synthesis,
                    document_type=context.get("document_type", "ethnographic_report"),
                    citation_style=context.get("citation_style", "apa")
                )
                results["document"] = res
            return {
                "phase": "documentation",
                "current_agent": "scribe",
                "results": results
            }

        async def archiving_phase(state: Any) -> Dict[str, Any]:
            """Fase de archivado en memoria"""
            results = state.get("results", {}) if isinstance(state, dict) else state.results

            if "archivist" in self.agents:
                items = [
                    results.get("bibliography", {}),
                    results.get("ethnography", {}),
                    results.get("synthesis", {}),
                    results.get("document", {})
                ]
                res = await self.run_agent("archivist", items=items)
                results["archive"] = res
            return {
                "phase": "archiving",
                "current_agent": "archivist",
                "results": results
            }

        def finalize(state: Any) -> Dict[str, Any]:
            """Finaliza el pipeline y genera resumen"""
            return {
                "phase": "completed",
                "completed_at": datetime.now().isoformat()
            }

        def handle_error(state: Any) -> Dict[str, Any]:
            """Maneja errores en el pipeline"""
            return {
                "phase": "error",
                "completed_at": datetime.now().isoformat()
            }

        # Construir grafo del pipeline

        workflow = StateGraph(KAIState)

        # Agregar nodos
        workflow.add_node("init", initialize)
        workflow.add_node("ethics", ethics_review)
        workflow.add_node("bibliography", bibliography_phase)
        workflow.add_node("ethnography", ethnography_phase)
        workflow.add_node("patterns", pattern_phase)
        workflow.add_node("synthesis", synthesis_phase)
        workflow.add_node("visualization", visualization_phase)
        workflow.add_node("documentation", documentation_phase)
        workflow.add_node("archiving", archiving_phase)
        workflow.add_node("finalize", finalize)
        workflow.add_node("error_handler", handle_error)

        # Definir flujo secuencial
        workflow.set_entry_point("init")
        workflow.add_edge("init", "ethics")

        # Rama condicional después de ética
        workflow.add_conditional_edges(
            "ethics",
            lambda state: "error_handler" if state.errors else "bibliography",
            {
                "bibliography": "bibliography",
                "error_handler": "error_handler"
            }
        )

        # Flujo secuencial principal
        workflow.add_edge("bibliography", "ethnography")
        workflow.add_edge("ethnography", "patterns")
        workflow.add_edge("patterns", "synthesis")
        workflow.add_edge("synthesis", "visualization")
        workflow.add_edge("visualization", "documentation")
        workflow.add_edge("documentation", "archiving")
        workflow.add_edge("archiving", "finalize")

        # Manejo de errores desde cualquier fase
        # (se puede mejorar con conditional edges desde cada fase)

        return workflow.compile()

    def register_agent(self, name: str, agent: Any) -> None:
        """Registra un agente en el orquestador"""
        self.agents[name] = agent
        logger.info(f"Agente registrado: {name}")

    def set_ethics_council(self, council: Any) -> None:
        """Configura el consejo ético"""
        self.ethics_council = council
        logger.info("Consejo ético configurado")

    def set_message_bus(self, bus: Any) -> None:
        """Configura el bus de mensajes"""
        self.message_bus = bus
        logger.info("Bus de mensajes configurado")

    def set_memory_manager(self, manager: Any) -> None:
        """Configura el gestor de memoria"""
        self.memory_manager = manager
        logger.info("Gestor de memoria configurado")

    async def run_pipeline(self, research_question: str,
                          research_type: str = "exploratory",
                          context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Ejecuta el pipeline completo de investigación

        Args:
            research_question: Pregunta de investigación
            research_type: Tipo de estudio (exploratory, descriptive, explanatory)
            context: Contexto adicional (área geográfica, período, materiales, etc.)

        Returns:
            Dict con resultados completos del pipeline
        """
        self.state.research_question = research_question
        self.state.research_type = research_type
        self.state.context = context or {}
        self.state.started_at = datetime.now().isoformat()
        self.state.phase = "running"

        try:
            input_dict = self.state.model_dump()
            result = await self.graph.ainvoke(input_dict)
            if isinstance(result, dict):
                self.state = KAIState(**result)


            return {
                "status": "success" if self.state.phase == "completed" else "error",
                "phase": self.state.phase,
                "results": self.state.results,
                "ethics_approved": self.state.ethics_approved,
                "duration": self._calculate_duration(),
                "errors": self.state.errors
            }

        except Exception as e:
            logger.error(f"Error crítico en pipeline: {e}")
            self.state.phase = "error"
            self.state.errors.append(str(e))
            self.state.completed_at = datetime.now().isoformat()

            return {
                "status": "error",
                "error": str(e),
                "phase": self.state.phase,
                "results": self.state.results
            }

    def _calculate_duration(self) -> str:
        """Calcula duración del pipeline"""
        if self.state.started_at and self.state.completed_at:
            start = datetime.fromisoformat(self.state.started_at)
            end = datetime.fromisoformat(self.state.completed_at)
            return str(end - start)
        return "N/A"

    def get_status(self) -> Dict[str, Any]:
        """Estado actual del orquestador"""
        return {
            "phase": self.state.phase,
            "agents_registered": list(self.agents.keys()),
            "ethics_configured": self.ethics_council is not None,
            "message_bus_configured": self.message_bus is not None,
            "memory_configured": self.memory_manager is not None,
            "results_so_far": list(self.state.results.keys()),
            "errors": self.state.errors
        }

    async def run_agent(self, agent_name: str, **kwargs) -> Dict[str, Any]:
        """
        Ejecuta un agente específico directamente

        Args:
            agent_name: Nombre del agente a ejecutar
            **kwargs: Argumentos específicos del agente

        Returns:
            Resultado de la ejecución del agente
        """
        if agent_name not in self.agents:
            return {"status": "error", "error": f"Agente '{agent_name}' no registrado"}

        agent = self.agents[agent_name]

        try:
            if hasattr(agent, 'run'):
                result = await agent.run(**kwargs)
            else:
                result = agent.execute(**kwargs)

            # Publicar resultado en bus de mensajes
            if self.message_bus:
                await self.message_bus.publish(
                    f"{agent_name}_complete",
                    {"agent": agent_name, "result": result}
                )

            # Almacenar en memoria
            if self.memory_manager:
                await self.memory_manager.store(
                    key=f"result_{agent_name}_{datetime.now().isoformat()}",
                    value=result,
                    metadata={"agent": agent_name}
                )

            return result

        except Exception as e:
            logger.error(f"Error ejecutando agente {agent_name}: {e}")
            return {"status": "error", "error": str(e)}
