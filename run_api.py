# run_api.py

import logging
import uvicorn

from api.main import app

try:
    from utils.ascii_logo import print_startup_logo, get_mini_logo
    LOGO_AVAILABLE = True
except ImportError:
    LOGO_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    # Mostrar logo de inicio
    if LOGO_AVAILABLE:
        print_startup_logo("1.0.0", True)
        logger.info(f"{get_mini_logo()} - Iniciando servidor API...")
    else:
        logger.info("🧠 KOGNITO AI - Iniciando servidor API desde run_api.py...")

    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
