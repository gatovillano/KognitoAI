# run_api.py

import logging
import uvicorn
from utils.ascii_logo import print_startup_logo

from api.main import app

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    print_startup_logo("1.0.0")
    logger.info("Iniciando servidor API desde run_api.py...")
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
