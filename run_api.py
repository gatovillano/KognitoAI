# run_api.py

import logging
import uvicorn
import asyncio # Importar asyncio
from utils.ascii_logo import print_startup_logo
from utils.embeddings import initialize_embeddings # Importar la función de inicialización

from api.main import app

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    print_startup_logo("1.0.0")
    logger.info("Iniciando servidor API desde run_api.py...")
    # Inicializar embeddings de forma asíncrona antes de iniciar el servidor Uvicorn
    await initialize_embeddings()
    # Iniciar Uvicorn de forma programática
    config = uvicorn.Config("api.main:app", host="0.0.0.0", port=8000, reload=True)
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
