"""
KAI-Ethno Orchestrator
Orquestador principal del pipeline de investigación antropológica
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
skill_dir = os.path.dirname(current_dir)
if skill_dir not in sys.path:
    sys.path.insert(0, skill_dir)

try:
    from ..agents.archivist import ArchivistAgent, ArchivistState
    from ..agents.bibliomancer import BibliomancerAgent, BibliomancerState
    from ..agents.ethnograph import EthnographAgent, EthnographState
    from ..agents.pattern_finder import PatternFinderAgent, PatternFinderState
    from ..agents.scribe import ScribeAgent, ScribeState
    from ..agents.synthesizer import SynthesizerAgent, SynthesizerState
    from ..agents.visualizer import VisualizerAgent, VisualizerState
    from ..core.ethics_council import EthicsCouncil, EthicsVerdict
    from ..core.message_bus import MessageBus, MessageType
except (ImportError, ValueError):
    from agents.archivist import ArchivistAgent, ArchivistState
    from agents.bibliomancer import BibliomancerAgent, BibliomancerState
    from agents.ethnograph import EthnographAgent, EthnographState
    from agents.pattern_finder import PatternFinderAgent, PatternFinderState
    from agents.scribe import ScribeAgent, ScribeState
    from agents.synthesizer import SynthesizerAgent, SynthesizerState
    from agents.visualizer import VisualizerAgent, VisualizerState
    from core.ethics_council import EthicsCouncil, EthicsVerdict
    from core.message_bus import MessageBus, MessageType

logger = logging.getLogger(__name__)


class KAIEthnoOrchestrator:
    """
    Orquestador principal de KAI-Ethno.
    Gestiona el flujo completo de investigación antropológica.
    """

    def __init__(
        self,
        enable_ethics: bool = True,
        enable_memory: bool = True,
        enable_message_bus: bool = True,
        output_dir: str = "./output",
    ):
        self.enable_ethics = enable_ethics
        self.enable_memory = enable_memory
        self.enable_message_bus = enable_message_bus
        self.output_dir = output_dir

        # Inicializar componentes core
        self.message_bus = MessageBus() if enable_message_bus else None
        self.ethics_council = EthicsCouncil() if enable_ethics else None

        # Inicializar agentes
        self.bibliomancer = BibliomancerAgent()
        self.ethnograph = EthnographAgent()
        self.pattern_finder = PatternFinderAgent()
        self.synthesizer = SynthesizerAgent()
        self.visualizer = VisualizerAgent()
        self.scribe = ScribeAgent()
        self.archivist = ArchivistAgent()

        # Estado del pipeline
        self._initialized = False
        self.pipeline_state: Dict[str, Any] = {}
        self.execution_log: List[Dict[str, Any]] = []

    async def run_research(
        self,
        research_question: str,
        max_sources: int = 100,
        year_range: tuple = (2020, 2025),
        include_visualizations: bool = True,
        generate_document: bool = True,
        document_type: str = "ethnographic_report",
        citation_style: str = "apa",
        skip_ethics: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Ejecuta el pipeline completo de investigación.

        Args:
            research_question: Pregunta de investigación
            max_sources: Número máximo de fuentes a recolectar
            year_range: Rango de años (tupla)
            include_visualizations: Generar visualizaciones
            generate_document: Generar documento académico
            document_type: Tipo de documento (ethnographic_report, literature_review, imrad)
            citation_style: Estilo de citación (apa, mla, chicago, aaa)
            skip_ethics: Omitir revisión ética (solo para testing)
            **kwargs: Argumentos adicionales

        Returns:
            Diccionario con todos los resultados del pipeline
        """
        # Inicializar orquestador si es necesario
        await self.initialize()

        start_time = datetime.now()
        logger.info(f"Iniciando investigación: {research_question}")
        self._log_event("pipeline_start", {"research_question": research_question})

        results = {
            "research_question": research_question,
            "timestamp": start_time.isoformat(),
            "status": "running",
            "stages": {},
        }

        try:
            # Etapa 1: Recolección bibliográfica
            sources = await self._stage_bibliographic_search(
                research_question, max_sources, year_range
            )
            results["stages"]["bibliographic"] = sources
            results["sources_count"] = len(sources.get("sources", []))

            # Etapa 2: Validación ética (después de recolección)
            if self.enable_ethics and not skip_ethics:
                ethics_ok = await self._stage_ethics_review(sources, "bibliographic")
                if not ethics_ok:
                    results["status"] = "blocked_by_ethics"
                    results["ethics_block"] = True
                    logger.warning("Pipeline bloqueado por Ethics Council")
                    return results
                results["stages"]["ethics_bibliographic"] = {"passed": True}

            # Etapa 3: Procesamiento etnográfico
            processed = await self._stage_ethnographic_processing(sources)
            results["stages"]["ethnographic"] = processed

            # Etapa 4: Minería de patrones
            patterns = await self._stage_pattern_mining(processed)
            results["stages"]["patterns"] = patterns

            # Etapa 5: Síntesis
            synthesis = await self._stage_synthesis(patterns, sources)
            results["stages"]["synthesis"] = synthesis

            # Etapa 6: Visualizaciones (opcional)
            if include_visualizations:
                visuals = await self._stage_visualization(patterns, synthesis)
                results["stages"]["visualizations"] = visuals

            # Etapa 7: Redacción (opcional)
            if generate_document:
                document = await self._stage_document_generation(
                    research_question=research_question,
                    sources=sources,
                    patterns=patterns,
                    synthesis=synthesis,
                    document_type=document_type,
                    citation_style=citation_style,
                )
                results["stages"]["document"] = document

            # Etapa 8: Archivado
            archive = await self._stage_archiving(
                sources=sources,
                patterns=patterns,
                synthesis=synthesis,
                include_visualizations=include_visualizations,
                generate_document=generate_document,
            )
            results["stages"]["archive"] = archive

            # Finalizar
            results["status"] = "completed"
            results["execution_time"] = (datetime.now() - start_time).total_seconds()
            logger.info(f"Investigación completada en {results['execution_time']:.2f}s")
            self._log_event("pipeline_complete", {"execution_time": results["execution_time"]})

        except Exception as e:
            logger.error(f"Error en pipeline: {e}", exc_info=True)
            results["status"] = "error"
            results["error"] = str(e)
            self._log_event("pipeline_error", {"error": str(e)})

        return results

    async def _stage_bibliographic_search(
        self, query: str, max_results: int, year_range: tuple
    ) -> Dict[str, Any]:
        """Etapa 1: Búsqueda bibliográfica"""
        logger.info("Etapa 1: Búsqueda bibliográfica")
        self._log_event("stage_start", {"stage": "bibliographic"})

        result = await self.bibliomancer.search(
            query=query, max_results=max_results, year_range=year_range
        )

        self._log_event("stage_complete", {"stage": "bibliographic", "count": len(result.get("sources", []))})
        return result

    async def _stage_ethics_review(
        self, data: Dict[str, Any], context: str
    ) -> bool:
        """Etapa 2: Revisión ética"""
        logger.info(f"Etapa ética: Revisión de {context}")
        self._log_event("ethics_review", {"context": context})

        verdict = await self.ethics_council.review(data, context=context)

        if verdict == EthicsVerdict.VETO:
            logger.warning(f"Veto ético en etapa: {context}")
            self._log_event("ethics_veto", {"context": context})
            return False

        self._log_event("ethics_approved", {"context": context})
        return True

    async def _stage_ethnographic_processing(
        self, sources: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Etapa 3: Procesamiento etnográfico"""
        logger.info("Etapa 3: Procesamiento etnográfico")
        self._log_event("stage_start", {"stage": "ethnographic"})

        result = await self.ethnograph.process_corpus(sources)

        self._log_event("stage_complete", {"stage": "ethnographic"})
        return result

    async def _stage_pattern_mining(
        self, processed: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Etapa 4: Minería de patrones"""
        logger.info("Etapa 4: Minería de patrones")
        self._log_event("stage_start", {"stage": "patterns"})

        result = await self.pattern_finder.analyze(processed)

        self._log_event("stage_complete", {"stage": "patterns"})
        return result

    async def _stage_synthesis(
        self, patterns: Dict[str, Any], sources: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Etapa 5: Síntesis"""
        logger.info("Etapa 5: Síntesis")
        self._log_event("stage_start", {"stage": "synthesis"})

        result = await self.synthesizer.synthesize(patterns, sources)

        self._log_event("stage_complete", {"stage": "synthesis"})
        return result

    async def _stage_visualization(
        self, patterns: Dict[str, Any], synthesis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Etapa 6: Visualizaciones"""
        logger.info("Etapa 6: Generación de visualizaciones")
        self._log_event("stage_start", {"stage": "visualizations"})

        viz_data = {
            "keywords": patterns.get("keywords", {}),
            "networks": patterns.get("networks", []),
            "temporal": patterns.get("temporal", {}),
            "clusters": patterns.get("clusters", []),
            "synthesis_summary": synthesis.get("summary", {}),
        }

        result = await self.visualizer.run(viz_data)

        self._log_event("stage_complete", {"stage": "visualizations"})
        return result

    async def _stage_document_generation(
        self,
        research_question: str,
        sources: Dict[str, Any],
        patterns: Dict[str, Any],
        synthesis: Dict[str, Any],
        document_type: str,
        citation_style: str,
    ) -> Dict[str, Any]:
        """Etapa 7: Redacción de documento"""
        logger.info(f"Etapa 7: Redacción de documento ({document_type})")
        self._log_event("stage_start", {"stage": "document", "type": document_type})

        result = await self.scribe.run(
            research_question=research_question,
            sources=sources,
            analysis_results=synthesis,
            patterns=patterns,
            document_type=document_type,
            citation_style=citation_style,
        )

        self._log_event("stage_complete", {"stage": "document"})
        return result

    async def _stage_archiving(
        self,
        sources: Dict[str, Any],
        patterns: Dict[str, Any],
        synthesis: Dict[str, Any],
        include_visualizations: bool,
        generate_document: bool,
    ) -> Dict[str, Any]:
        """Etapa 8: Archivado"""
        logger.info("Etapa 8: Archivado")
        self._log_event("stage_start", {"stage": "archive"})

        # Preparar items para archivar
        items = [sources, patterns, synthesis]

        result = await self.archivist.run(items)

        self._log_event("stage_complete", {"stage": "archive"})
        return result

    def _log_event(self, event_type: str, data: Dict[str, Any]):
        """Registra evento en el log del pipeline"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "data": data,
        }
        self.execution_log.append(event)

        # Publicar en bus de mensajes si está habilitado
        if self.message_bus:
            asyncio.create_task(
                self.message_bus.publish(
                    topic="pipeline.events",
                    message=event,
                    message_type=MessageType.EVENT,
                )
            )

    async def get_status(self) -> Dict[str, Any]:
        """Obtiene el estado actual del pipeline"""
        return {
            "pipeline_state": self.pipeline_state,
            "execution_log": self.execution_log[-10:],  # Últimos 10 eventos
            "agents": {
                "bibliomancer": "ready",
                "ethnograph": "ready",
                "pattern_finder": "ready",
                "synthesizer": "ready",
                "visualizer": "ready",
                "scribe": "ready",
                "archivist": "ready",
            },
        }

    async def initialize(self):
        """Inicializa el orquestador y sus componentes"""
        if self._initialized:
            return

        if self.message_bus:
            await self.message_bus.start()
            await self._setup_agent_subscriptions()

        self._initialized = True
        logger.info("Orquestador inicializado correctamente")

    async def _setup_agent_subscriptions(self):
        """Configura suscripciones entre agentes en el bus de mensajes"""
        if not self.message_bus:
            return

        # Suscribir agentes a eventos relevantes
        subscriptions = {
            "pipeline.stage.complete": [
                self._on_stage_complete,
            ],
            "pipeline.error": [
                self._on_pipeline_error,
            ],
            "ethics.verdict": [
                self._on_ethics_verdict,
            ],
        }

        for topic, callbacks in subscriptions.items():
            for callback in callbacks:
                self.message_bus.subscribe(topic, callback)

        self._agent_subscriptions = {
            topic: [cb.__name__ for cb in cbs]
            for topic, cbs in subscriptions.items()
        }

        logger.debug(f"Suscripciones configuradas: {self._agent_subscriptions}")

    async def _on_stage_complete(self, message):
        """Maneja eventos de etapa completada"""
        stage = message.payload.get("stage")
        if stage:
            self.pipeline_state[stage] = "completed"
            logger.debug(f"Etapa completada: {stage}")

    async def _on_pipeline_error(self, message):
        """Maneja errores del pipeline"""
        error = message.payload.get("error")
        logger.error(f"Error en pipeline: {error}")

    async def _on_ethics_verdict(self, message):
        """Maneja veredictos del Ethics Council"""
        verdict = message.payload.get("verdict")
        context = message.payload.get("context")
        logger.info(f"Veredicto ético en '{context}': {verdict}")
    async def shutdown(self):
        """Cierra todos los recursos"""
        logger.info("Cerrando orquestador...")

        if self.message_bus:
            await self.message_bus.shutdown()

        logger.info("Orquestador cerrado correctamente")
