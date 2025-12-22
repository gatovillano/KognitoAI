# tools/background_task_manager.py
"""
Gestor de tareas en background para procesamiento conceptual.
Permite consultar el estado de tareas de larga duración.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class BackgroundTaskManager:
    """
    Gestor centralizado para tareas en background.
    Mantiene un registro de todas las tareas de procesamiento conceptual.
    """
    
    _tasks: Dict[str, Dict[str, Any]] = {}
    _lock: bool = False  # Simple lock para thread safety
    
    @classmethod
    def create_task(cls, task_id: str, account_id: str, workspace_id: Optional[str] = None, 
                   task_type: str = "conceptual_processing") -> Dict[str, Any]:
        """Crea una nueva tarea en background."""
        task_info = {
            "id": task_id,
            "type": task_type,
            "status": "created",
            "account_id": account_id,
            "workspace_id": workspace_id,
            "created_at": datetime.now().isoformat(),
            "start_time": None,
            "end_time": None,
            "progress": 0,
            "message": "Tarea creada"
        }
        
        cls._tasks[task_id] = task_info
        logger.info(f"📋 Tarea creada: {task_id} (tipo: {task_type})")
        return task_info
    
    @classmethod
    def update_task(cls, task_id: str, status: str = None, progress: int = None, 
                   message: str = None, result: Any = None, error: str = None) -> bool:
        """Actualiza el estado de una tarea."""
        if task_id not in cls._tasks:
            logger.warning(f"⚠️ Intento de actualizar tarea inexistente: {task_id}")
            return False
        
        task = cls._tasks[task_id]
        
        if status:
            task["status"] = status
            if status == "running" and not task.get("start_time"):
                task["start_time"] = datetime.now().isoformat()
            elif status in ["completed", "failed", "cancelled"]:
                task["end_time"] = datetime.now().isoformat()
        
        if progress is not None:
            task["progress"] = max(0, min(100, progress))
        
        if message:
            task["message"] = message
        
        if result is not None:
            task["result"] = result
        
        if error:
            task["error"] = error
            task["status"] = "failed"
        
        logger.debug(f"📊 Tarea actualizada: {task_id} - Status: {status}, Progress: {progress}%")
        return True
    
    @classmethod
    def get_task(cls, task_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene información de una tarea específica."""
        return cls._tasks.get(task_id)
    
    @classmethod
    def list_tasks(cls, account_id: Optional[str] = None, status: Optional[str] = None, 
                  limit: int = 50) -> List[Dict[str, Any]]:
        """Lista tareas con filtros opcionales."""
        tasks = list(cls._tasks.values())
        
        # Filtrar por account_id
        if account_id:
            tasks = [task for task in tasks if task.get("account_id") == account_id]
        
        # Filtrar por status
        if status:
            tasks = [task for task in tasks if task.get("status") == status]
        
        # Ordenar por fecha de creación (más recientes primero)
        tasks.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        # Aplicar límite
        return tasks[:limit]
    
    @classmethod
    def delete_task(cls, task_id: str) -> bool:
        """Elimina una tarea del registro."""
        if task_id in cls._tasks:
            del cls._tasks[task_id]
            logger.info(f"🗑️ Tarea eliminada: {task_id}")
            return True
        return False
    
    @classmethod
    def cleanup_old_tasks(cls, max_age_hours: int = 24) -> int:
        """Limpia tareas completadas más antiguas que max_age_hours."""
        cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
        tasks_to_delete = []
        
        for task_id, task in cls._tasks.items():
            end_time = task.get("end_time")
            if end_time:
                try:
                    end_timestamp = datetime.fromisoformat(end_time).timestamp()
                    if end_timestamp < cutoff_time:
                        tasks_to_delete.append(task_id)
                except ValueError:
                    # Si no se puede parsear la fecha, mantener la tarea
                    pass
        
        for task_id in tasks_to_delete:
            del cls._tasks[task_id]
        
        if tasks_to_delete:
            logger.info(f"🧹 Limpieza completada: {len(tasks_to_delete)} tareas eliminadas")
        
        return len(tasks_to_delete)
    
    @classmethod
    def get_statistics(cls) -> Dict[str, Any]:
        """Obtiene estadísticas de las tareas."""
        total_tasks = len(cls._tasks)
        status_counts = {}
        type_counts = {}
        
        for task in cls._tasks.values():
            status = task.get("status", "unknown")
            task_type = task.get("type", "unknown")
            
            status_counts[status] = status_counts.get(status, 0) + 1
            type_counts[task_type] = type_counts.get(task_type, 0) + 1
        
        return {
            "total_tasks": total_tasks,
            "status_distribution": status_counts,
            "type_distribution": type_counts,
            "active_tasks": status_counts.get("running", 0),
            "completed_tasks": status_counts.get("completed", 0),
            "failed_tasks": status_counts.get("failed", 0)
        }
