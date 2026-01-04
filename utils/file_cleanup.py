# utils/file_cleanup.py

import os
import time
import logging
from datetime import datetime, timedelta
from api.galleries import MEDIA_ROOT

logger = logging.getLogger(__name__)

def cleanup_old_generated_files(max_age_hours: int = 24):
    """
    Elimina archivos en los directorios de salida generados que tengan más de max_age_hours.
    """
    directories = [
        os.path.join(MEDIA_ROOT, "generated_pdfs"),
        os.path.join(MEDIA_ROOT, "generated_data")
    ]
    
    now = time.time()
    cutoff = now - (max_age_hours * 3600)
    files_deleted = 0
    
    logger.info(f"🧹 Iniciando limpieza de archivos generados (antigüedad > {max_age_hours}h)...")
    
    for directory in directories:
        if not os.path.exists(directory):
            continue
            
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            
            # Solo procesar archivos, no directorios
            if not os.path.isfile(file_path):
                continue
                
            try:
                file_mtime = os.path.getmtime(file_path)
                if file_mtime < cutoff:
                    os.remove(file_path)
                    files_deleted += 1
                    logger.debug(f"🗑️ Archivo eliminado: {file_path}")
            except Exception as e:
                logger.error(f"❌ Error al eliminar {file_path}: {e}")
                
    if files_deleted > 0:
        logger.info(f"✅ Limpieza completada. Se eliminaron {files_deleted} archivos.")
    else:
        logger.info("✨ No se encontraron archivos viejos para limpiar.")
        
    return files_deleted
