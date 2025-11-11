# run_api.py

import logging
import uvicorn
import sys
from utils.ascii_logo import print_startup_logo

from api.main import app

# Restaura el manejador de excepciones por defecto para desactivar los tracebacks de 'rich'
sys.excepthook = sys.__excepthook__

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    print_startup_logo("1.0.0")
    logger.info("Iniciando servidor API desde run_api.py...")

    # Configurar loggers de Uvicorn para depuración
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)

    # Asegurarse de que los logs de core.tools se muestren
    tools_logger = logging.getLogger("core.tools")
    tools_logger.setLevel(logging.DEBUG)
    logger.info(f"Nivel de logging para core.tools: {logging.getLevelName(tools_logger.level)}")

    # AÑADIR ESTA LÍNEA: Asegurarse de que los logs de utils.security se muestren
    security_logger = logging.getLogger("utils.security")
    security_logger.setLevel(logging.DEBUG)
    logger.info(f"Nivel de logging para utils.security: {logging.getLevelName(security_logger.level)}")

    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
