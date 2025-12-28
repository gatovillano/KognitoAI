# knowledge_graph/progress_tracker.py
"""
Sistema de seguimiento de progreso para procesamiento de grafos de conocimiento.
Permite monitorear el avance de las diferentes fases en tiempo real.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class ProcessingPhase(Enum):
    """Fases del procesamiento de grafos."""
    # Fases comunes
    INITIALIZING = "initializing"
    FETCHING_DOCUMENTS = "fetching_documents"
    RECONSTRUCTING_CONTENT = "reconstructing_content"
    
    # Fases del procesamiento híbrido
    HYBRID_EXTRACTING_ENTITIES = "hybrid_extracting_entities"
    HYBRID_DEDUPLICATING = "hybrid_deduplicating"
    HYBRID_SEMANTIC_RELATIONSHIPS = "hybrid_semantic_relationships"
    HYBRID_COOCCURRENCE = "hybrid_cooccurrence"
    HYBRID_LLM_ENRICHMENT = "hybrid_llm_enrichment"
    
    # Fases del procesamiento conceptual
    CONCEPTUAL_CREATING_DOCUMENTS = "conceptual_creating_documents"
    CONCEPTUAL_EXTRACTING_QUOTES = "conceptual_extracting_quotes"
    CONCEPTUAL_THEMATIC_RELATIONSHIPS = "conceptual_thematic_relationships"
    CONCEPTUAL_IDEA_PROFILES = "conceptual_idea_profiles"
    
    # Fases finales
    SAVING_TO_NEO4J = "saving_to_neo4j"
    COMPLETED = "completed"
    ERROR = "error"


class ProgressTracker:
    """
    Rastreador de progreso para procesamiento de grafos.
    
    Uso:
        tracker = ProgressTracker(task_id="abc123", total_phases=5)
        tracker.update_phase(ProcessingPhase.HYBRID_EXTRACTING_ENTITIES, "Extrayendo entidades...", 20)
        tracker.update_phase(ProcessingPhase.HYBRID_SEMANTIC_RELATIONSHIPS, "Creando relaciones...", 60)
        tracker.complete()
    """
    
    def __init__(
        self, 
        task_id: Optional[str] = None,
        processing_mode: str = "hybrid",
        total_phases: int = 5,
        on_progress: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        """
        Inicializa el tracker de progreso.
        
        Args:
            task_id: ID único de la tarea (se genera uno si no se proporciona)
            processing_mode: Modo de procesamiento ("hybrid" o "conceptual")
            total_phases: Número total de fases del procesamiento
            on_progress: Callback opcional que se llama en cada actualización
        """
        self.task_id = task_id or str(uuid.uuid4())[:8]
        self.processing_mode = processing_mode
        self.total_phases = total_phases
        self.on_progress = on_progress
        
        # Estado interno
        self.current_phase: ProcessingPhase = ProcessingPhase.INITIALIZING
        self.current_phase_index: int = 0
        self.progress_percent: float = 0.0
        self.message: str = "Iniciando procesamiento..."
        self.details: Dict[str, Any] = {}
        self.started_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()
        self.completed_at: Optional[datetime] = None
        self.error: Optional[str] = None
        self.phase_history: List[Dict[str, Any]] = []
        
        # Métricas acumuladas
        self.entities_count: int = 0
        self.relationships_count: int = 0
        self.documents_processed: int = 0
        self.quotes_extracted: int = 0
        
        logger.info(f"📊 ProgressTracker iniciado - Task ID: {self.task_id}, Modo: {processing_mode}")
    
    def update_phase(
        self, 
        phase: ProcessingPhase, 
        message: str, 
        progress_percent: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Actualiza la fase actual del procesamiento.
        
        Args:
            phase: Nueva fase del procesamiento
            message: Mensaje descriptivo para mostrar al usuario
            progress_percent: Porcentaje de progreso (0-100). Si es None, se calcula automáticamente.
            details: Detalles adicionales (conteos, estadísticas, etc.)
        """
        self.current_phase = phase
        self.current_phase_index += 1
        self.message = message
        self.updated_at = datetime.now()
        
        # Calcular progreso automáticamente si no se proporciona
        if progress_percent is not None:
            self.progress_percent = min(100.0, max(0.0, progress_percent))
        else:
            self.progress_percent = min(100.0, (self.current_phase_index / self.total_phases) * 100)
        
        # Actualizar detalles
        if details:
            self.details.update(details)
            # Actualizar métricas acumuladas
            if "entities_count" in details:
                self.entities_count = details["entities_count"]
            if "relationships_count" in details:
                self.relationships_count = details["relationships_count"]
            if "documents_processed" in details:
                self.documents_processed = details["documents_processed"]
            if "quotes_extracted" in details:
                self.quotes_extracted = details["quotes_extracted"]
        
        # Guardar en historial
        self.phase_history.append({
            "phase": phase.value,
            "message": message,
            "progress": self.progress_percent,
            "timestamp": self.updated_at.isoformat()
        })
        
        # Log del progreso
        logger.info(f"📊 [{self.task_id}] {phase.value}: {message} ({self.progress_percent:.0f}%)")
        
        # Llamar callback si existe
        if self.on_progress:
            try:
                self.on_progress(self.get_status())
            except Exception as e:
                logger.error(f"Error en callback de progreso: {e}")
    
    def update_sub_progress(self, sub_message: str, sub_progress: float) -> None:
        """
        Actualiza el progreso dentro de una fase sin cambiar de fase.
        Útil para mostrar progreso granular en fases largas.
        
        Args:
            sub_message: Mensaje descriptivo del sub-progreso
            sub_progress: Porcentaje de progreso dentro de la fase actual (0-100)
        """
        self.message = sub_message
        self.updated_at = datetime.now()
        
        # Calcular progreso global basado en sub-progreso
        phase_start = ((self.current_phase_index - 1) / self.total_phases) * 100
        phase_end = (self.current_phase_index / self.total_phases) * 100
        phase_range = phase_end - phase_start
        
        self.progress_percent = phase_start + (sub_progress / 100 * phase_range)
        
        logger.debug(f"📊 [{self.task_id}] Sub-progreso: {sub_message} ({self.progress_percent:.0f}%)")
        
        # Llamar callback si existe
        if self.on_progress:
            try:
                self.on_progress(self.get_status())
            except Exception as e:
                logger.error(f"Error en callback de progreso: {e}")
    
    def complete(self, final_message: Optional[str] = None) -> None:
        """
        Marca el procesamiento como completado.
        
        Args:
            final_message: Mensaje final opcional
        """
        self.current_phase = ProcessingPhase.COMPLETED
        self.progress_percent = 100.0
        self.message = final_message or "✅ Procesamiento completado exitosamente"
        self.completed_at = datetime.now()
        self.updated_at = datetime.now()
        
        duration = (self.completed_at - self.started_at).total_seconds()
        
        self.details["duration_seconds"] = round(duration, 2)
        self.details["final_entities"] = self.entities_count
        self.details["final_relationships"] = self.relationships_count
        
        logger.info(f"🎉 [{self.task_id}] Completado en {duration:.1f}s - Entidades: {self.entities_count}, Relaciones: {self.relationships_count}")
        
        # Llamar callback final
        if self.on_progress:
            try:
                self.on_progress(self.get_status())
            except Exception as e:
                logger.error(f"Error en callback de progreso: {e}")
    
    def set_error(self, error_message: str) -> None:
        """
        Marca el procesamiento con error.
        
        Args:
            error_message: Descripción del error
        """
        self.current_phase = ProcessingPhase.ERROR
        self.error = error_message
        self.message = f"❌ Error: {error_message}"
        self.updated_at = datetime.now()
        
        logger.error(f"❌ [{self.task_id}] Error: {error_message}")
        
        # Llamar callback de error
        if self.on_progress:
            try:
                self.on_progress(self.get_status())
            except Exception as e:
                logger.error(f"Error en callback de progreso: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Obtiene el estado actual del progreso.
        
        Returns:
            Dict con toda la información del progreso
        """
        duration = (self.updated_at - self.started_at).total_seconds()
        
        return {
            "task_id": self.task_id,
            "processing_mode": self.processing_mode,
            "phase": self.current_phase.value,
            "phase_index": self.current_phase_index,
            "total_phases": self.total_phases,
            "progress_percent": round(self.progress_percent, 1),
            "message": self.message,
            "is_complete": self.current_phase == ProcessingPhase.COMPLETED,
            "has_error": self.current_phase == ProcessingPhase.ERROR,
            "error": self.error,
            "metrics": {
                "entities_count": self.entities_count,
                "relationships_count": self.relationships_count,
                "documents_processed": self.documents_processed,
                "quotes_extracted": self.quotes_extracted
            },
            "timing": {
                "started_at": self.started_at.isoformat(),
                "updated_at": self.updated_at.isoformat(),
                "completed_at": self.completed_at.isoformat() if self.completed_at else None,
                "duration_seconds": round(duration, 2)
            },
            "details": self.details
        }


# Almacén global de progreso (en memoria)
# Para producción, considera usar Redis o similar
_progress_store: Dict[str, ProgressTracker] = {}


def create_progress_tracker(
    task_id: Optional[str] = None,
    processing_mode: str = "hybrid",
    total_phases: int = 5
) -> ProgressTracker:
    """
    Crea y registra un nuevo tracker de progreso.
    
    Args:
        task_id: ID único de la tarea
        processing_mode: Modo de procesamiento
        total_phases: Número total de fases
        
    Returns:
        ProgressTracker registrado
    """
    tracker = ProgressTracker(
        task_id=task_id,
        processing_mode=processing_mode,
        total_phases=total_phases
    )
    _progress_store[tracker.task_id] = tracker
    
    # Limpiar trackers antiguos (más de 1 hora)
    _cleanup_old_trackers()
    
    return tracker


def get_progress(task_id: str) -> Optional[Dict[str, Any]]:
    """
    Obtiene el estado de progreso de una tarea.
    
    Args:
        task_id: ID de la tarea
        
    Returns:
        Estado del progreso o None si no existe
    """
    tracker = _progress_store.get(task_id)
    return tracker.get_status() if tracker else None


def get_all_active_progress() -> List[Dict[str, Any]]:
    """
    Obtiene el progreso de todas las tareas activas.
    
    Returns:
        Lista de estados de progreso
    """
    return [
        tracker.get_status() 
        for tracker in _progress_store.values()
        if tracker.current_phase != ProcessingPhase.COMPLETED
    ]


def _cleanup_old_trackers() -> None:
    """Limpia trackers completados de más de 1 hora."""
    from datetime import timedelta
    
    cutoff = datetime.now() - timedelta(hours=1)
    to_delete = [
        task_id for task_id, tracker in _progress_store.items()
        if tracker.completed_at and tracker.completed_at < cutoff
    ]
    
    for task_id in to_delete:
        del _progress_store[task_id]
    
    if to_delete:
        logger.debug(f"🧹 Limpiados {len(to_delete)} trackers antiguos")
