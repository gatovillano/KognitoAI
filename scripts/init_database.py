#!/usr/bin/env python3
"""
Script para inicializar la base de datos con todas las tablas necesarias.
Ejecuta la función create_tables() para crear la estructura completa.
"""

import asyncio
import sys
import os
import logging

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import create_tables

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Inicializa la base de datos creando todas las tablas necesarias."""
    
    logger.info("🚀 Iniciando inicialización de la base de datos...")
    
    try:
        # Crear todas las tablas
        await create_tables()
        
        logger.info("✅ Base de datos inicializada exitosamente!")
        print("\n" + "=" * 50)
        print("✅ Inicialización completada!")
        print("\n💡 Tablas creadas:")
        print("- langchain_pg_collection")
        print("- langchain_pg_embedding (con columnas personalizadas)")
        print("- accounts, teams, workspaces")
        print("- chat_threads, analysis_tasks")
        print("- Y todas las demás tablas del sistema")
        print("\n🔧 El sistema está listo para usar.")
        
    except Exception as e:
        logger.error(f"❌ Error durante la inicialización: {e}")
        print(f"\n❌ Error: {e}")
        print("\n🔧 Verifica:")
        print("1. Que PostgreSQL esté corriendo")
        print("2. Que las credenciales de la base de datos sean correctas")
        print("3. Que la base de datos 'kognito_db' exista")
        raise

if __name__ == "__main__":
    asyncio.run(main())
