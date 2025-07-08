# api/logs.py

"""
API endpoints para acceder a los logs del LLM.
Permite ver los logs detallados de las comunicaciones con el LLM desde el frontend.
"""

import os
import glob
import logging
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from utils.security import get_current_account_id

logger = logging.getLogger(__name__)
router = APIRouter()

class LogEntry(BaseModel):
    timestamp: str
    level: str
    logger_name: str
    message: str
    line_number: Optional[int] = None
    function_name: Optional[str] = None

class LogFile(BaseModel):
    filename: str
    size: int
    modified: str
    is_current: bool

def get_llm_log_files() -> List[LogFile]:
    """Obtiene la lista de archivos de log del LLM disponibles."""
    log_pattern = "logs/llm_detailed_*.log"
    log_files = glob.glob(log_pattern)
    
    if not log_files:
        return []
    
    # Ordenar por fecha de modificación, más reciente primero
    log_files.sort(key=os.path.getmtime, reverse=True)
    
    result = []
    for i, log_file in enumerate(log_files):
        stat = os.stat(log_file)
        result.append(LogFile(
            filename=os.path.basename(log_file),
            size=stat.st_size,
            modified=datetime.fromtimestamp(stat.st_mtime).isoformat(),
            is_current=(i == 0)  # El más reciente es el actual
        ))
    
    return result

def parse_log_line(line: str) -> Optional[LogEntry]:
    """Parsea una línea de log y extrae la información estructurada."""
    if not line.strip():
        return None
    
    try:
        # Formato esperado: timestamp - logger_name - level - [function:line] - message
        parts = line.split(' - ', 4)
        if len(parts) < 4:
            return LogEntry(
                timestamp="",
                level="INFO",
                logger_name="unknown",
                message=line
            )
        
        timestamp = parts[0]
        logger_name = parts[1]
        level = parts[2]
        
        # Extraer función y línea si están presentes
        function_info = ""
        message = ""
        
        if len(parts) >= 5:
            function_info = parts[3]
            message = parts[4]
        else:
            message = parts[3]
        
        # Parsear información de función y línea
        function_name = None
        line_number = None
        
        if function_info.startswith('[') and function_info.endswith(']'):
            func_info = function_info[1:-1]  # Remover corchetes
            if ':' in func_info:
                func_parts = func_info.split(':')
                function_name = func_parts[0]
                try:
                    line_number = int(func_parts[1])
                except ValueError:
                    pass
        
        return LogEntry(
            timestamp=timestamp,
            level=level,
            logger_name=logger_name,
            message=message,
            function_name=function_name,
            line_number=line_number
        )
    
    except Exception as e:
        logger.warning(f"Error parseando línea de log: {e}")
        return LogEntry(
            timestamp="",
            level="INFO",
            logger_name="parser_error",
            message=line
        )

@router.get("/logs/llm/files", response_model=List[LogFile])
async def get_log_files(current_account_id: str = Depends(get_current_account_id)):
    """Obtiene la lista de archivos de log del LLM disponibles."""
    try:
        return get_llm_log_files()
    except Exception as e:
        logger.error(f"Error obteniendo archivos de log: {e}")
        raise HTTPException(status_code=500, detail="Error obteniendo archivos de log")

@router.get("/logs/llm/content")
async def get_log_content(
    filename: Optional[str] = Query(None, description="Nombre del archivo de log"),
    lines: int = Query(100, description="Número de líneas a obtener"),
    filter_level: Optional[str] = Query(None, description="Filtrar por nivel de log"),
    filter_logger: Optional[str] = Query(None, description="Filtrar por nombre de logger"),
    current_account_id: str = Depends(get_current_account_id)
):
    """Obtiene el contenido de un archivo de log del LLM."""
    try:
        # Si no se especifica archivo, usar el más reciente
        if not filename:
            log_files = get_llm_log_files()
            if not log_files:
                raise HTTPException(status_code=404, detail="No se encontraron archivos de log")
            filename = log_files[0].filename
        
        log_path = f"logs/{filename}"
        
        if not os.path.exists(log_path):
            raise HTTPException(status_code=404, detail="Archivo de log no encontrado")
        
        # Leer las últimas N líneas
        with open(log_path, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
        
        # Tomar las últimas líneas
        recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        
        # Parsear y filtrar líneas
        log_entries = []
        for line in recent_lines:
            entry = parse_log_line(line.rstrip('\n'))
            if entry:
                # Aplicar filtros
                if filter_level and entry.level != filter_level:
                    continue
                if filter_logger and filter_logger.lower() not in entry.logger_name.lower():
                    continue
                
                log_entries.append(entry)
        
        return {
            "filename": filename,
            "total_lines": len(all_lines),
            "returned_lines": len(log_entries),
            "entries": log_entries
        }
    
    except Exception as e:
        logger.error(f"Error obteniendo contenido de log: {e}")
        raise HTTPException(status_code=500, detail="Error obteniendo contenido de log")

@router.get("/logs/llm/stream")
async def stream_log_content(
    filename: Optional[str] = Query(None, description="Nombre del archivo de log"),
    current_account_id: str = Depends(get_current_account_id)
):
    """Stream del contenido de un archivo de log en tiempo real."""
    try:
        # Si no se especifica archivo, usar el más reciente
        if not filename:
            log_files = get_llm_log_files()
            if not log_files:
                raise HTTPException(status_code=404, detail="No se encontraron archivos de log")
            filename = log_files[0].filename
        
        log_path = f"logs/{filename}"
        
        if not os.path.exists(log_path):
            raise HTTPException(status_code=404, detail="Archivo de log no encontrado")
        
        def generate_log_stream():
            try:
                with open(log_path, 'r', encoding='utf-8') as f:
                    # Ir al final del archivo
                    f.seek(0, 2)
                    
                    while True:
                        line = f.readline()
                        if line:
                            entry = parse_log_line(line.rstrip('\n'))
                            if entry:
                                yield f"data: {entry.model_dump_json()}\n\n"
                        else:
                            # No hay nuevas líneas, esperar un poco
                            import time
                            time.sleep(0.5)
            except Exception as e:
                yield f"data: {{'error': 'Error leyendo log: {str(e)}'}}\n\n"
        
        return StreamingResponse(
            generate_log_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
    
    except Exception as e:
        logger.error(f"Error en stream de log: {e}")
        raise HTTPException(status_code=500, detail="Error en stream de log")

@router.get("/logs/llm/search")
async def search_logs(
    query: str = Query(..., description="Término de búsqueda"),
    filename: Optional[str] = Query(None, description="Nombre del archivo de log"),
    max_results: int = Query(50, description="Máximo número de resultados"),
    current_account_id: str = Depends(get_current_account_id)
):
    """Busca en los logs del LLM por un término específico."""
    try:
        # Si no se especifica archivo, buscar en el más reciente
        if not filename:
            log_files = get_llm_log_files()
            if not log_files:
                raise HTTPException(status_code=404, detail="No se encontraron archivos de log")
            filename = log_files[0].filename
        
        log_path = f"logs/{filename}"
        
        if not os.path.exists(log_path):
            raise HTTPException(status_code=404, detail="Archivo de log no encontrado")
        
        # Buscar en el archivo
        matches = []
        with open(log_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                if query.lower() in line.lower():
                    entry = parse_log_line(line.rstrip('\n'))
                    if entry:
                        matches.append({
                            "line_number": line_num,
                            "entry": entry
                        })
                    
                    if len(matches) >= max_results:
                        break
        
        return {
            "query": query,
            "filename": filename,
            "total_matches": len(matches),
            "matches": matches
        }
    
    except Exception as e:
        logger.error(f"Error buscando en logs: {e}")
        raise HTTPException(status_code=500, detail="Error buscando en logs")
