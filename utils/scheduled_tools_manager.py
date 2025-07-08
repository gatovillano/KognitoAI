# utils/scheduled_tools_manager.py

"""
Gestor de Herramientas Programadas.

Este módulo se encarga de inicializar y gestionar todas las herramientas
que deben ejecutarse automáticamente en el sistema.
"""

import logging
from datetime import time
from typing import Optional, List, Dict, Any
from utils.tool_scheduler import tool_scheduler, schedule_daily_analysis, schedule_daily_insights
from core.database import SessionLocal, Account
from utils.db_session import DBSession
from sqlalchemy import select

logger = logging.getLogger(__name__)

class ScheduledToolsManager:
    """
    Gestor centralizado de herramientas programadas.
    """
    
    def __init__(self):
        self.initialized = False
        self.default_schedules = {
            "daily_analysis": {"hour": 2, "minute": 0},  # 2:00 AM
            "daily_insights": {"hour": 8, "minute": 0},  # 8:00 AM
            "weekly_cleanup": {"day": 6, "hour": 3, "minute": 0},  # Domingo 3:00 AM
        }
    
    async def initialize_scheduled_tools(self):
        """
        Inicializa todas las herramientas programadas del sistema.
        Se llama al arrancar la aplicación.
        """
        if self.initialized:
            logger.info("Las herramientas programadas ya están inicializadas.")
            return
            
        logger.info("Inicializando herramientas programadas...")
        
        try:
            # Programar análisis diario global
            await self._schedule_global_analysis()
            
            # Programar herramientas específicas por cuenta
            await self._schedule_per_account_tools()
            
            # Programar herramientas de mantenimiento
            await self._schedule_maintenance_tools()
            
            self.initialized = True
            logger.info("✅ Herramientas programadas inicializadas exitosamente")
            
        except Exception as e:
            logger.error(f"Error al inicializar herramientas programadas: {e}", exc_info=True)
    
    async def _schedule_global_analysis(self):
        """Programa análisis global del sistema."""
        config = self.default_schedules["daily_analysis"]
        success = await schedule_daily_analysis(
            account_id=None,  # Análisis global
            hour=config["hour"],
            minute=config["minute"]
        )
        
        if success:
            logger.info(f"✅ Análisis diario global programado para las {config['hour']:02d}:{config['minute']:02d}")
        else:
            logger.error("❌ Error al programar análisis diario global")
    
    async def _schedule_per_account_tools(self):
        """Programa herramientas específicas para cada cuenta activa."""
        async with DBSession(SessionLocal) as db:
            # Obtener todas las cuentas activas
            stmt = select(Account).where(Account.is_active == True)
            result = await db.execute(stmt)
            accounts = result.scalars().all()
            
            for account in accounts:
                account_id = str(account.id)
                
                # Programar insights diarios por cuenta
                config = self.default_schedules["daily_insights"]
                success = await schedule_daily_insights(
                    account_id=account_id,
                    hour=config["hour"],
                    minute=config["minute"]
                )
                
                if success:
                    logger.info(f"✅ Insights diarios programados para cuenta {account_id}")
                else:
                    logger.warning(f"⚠️ Error al programar insights para cuenta {account_id}")
    
    async def _schedule_maintenance_tools(self):
        """Programa herramientas de mantenimiento del sistema."""
        # Programar limpieza semanal
        await self._schedule_weekly_cleanup()
        
        # Programar backup de datos (si se implementa)
        # await self._schedule_weekly_backup()
    
    async def _schedule_weekly_cleanup(self):
        """Programa limpieza semanal de datos obsoletos."""
        async def weekly_cleanup_task(account_id: Optional[str] = None, **kwargs):
            """Tarea de limpieza semanal."""
            logger.info("Iniciando limpieza semanal programada...")
            
            # Aquí puedes agregar lógica de limpieza:
            # - Eliminar análisis antiguos
            # - Limpiar logs viejos
            # - Optimizar base de datos
            # - Etc.
            
            async with DBSession(SessionLocal) as db:
                # Ejemplo: limpiar análisis antiguos (más de 30 días)
                from datetime import datetime, timedelta
                cutoff_date = datetime.utcnow() - timedelta(days=30)
                
                # Aquí agregarías las queries de limpieza
                logger.info(f"Limpiando datos anteriores a {cutoff_date}")
                
            logger.info("Limpieza semanal completada.")
            return "Limpieza semanal ejecutada exitosamente"
        
        config = self.default_schedules["weekly_cleanup"]
        success = await tool_scheduler.schedule_weekly_tool(
            tool_name="weekly_cleanup",
            tool_function=weekly_cleanup_task,
            day_of_week=config["day"],  # Domingo
            execution_time=time(hour=config["hour"], minute=config["minute"])
        )
        
        if success:
            logger.info(f"✅ Limpieza semanal programada para domingos a las {config['hour']:02d}:{config['minute']:02d}")
        else:
            logger.error("❌ Error al programar limpieza semanal")
    
    async def add_account_scheduled_tools(self, account_id: str):
        """
        Agrega herramientas programadas para una nueva cuenta.
        
        Args:
            account_id: ID de la cuenta nueva
        """
        logger.info(f"Agregando herramientas programadas para nueva cuenta: {account_id}")
        
        # Programar insights diarios para la nueva cuenta
        config = self.default_schedules["daily_insights"]
        success = await schedule_daily_insights(
            account_id=account_id,
            hour=config["hour"],
            minute=config["minute"]
        )
        
        if success:
            logger.info(f"✅ Insights diarios programados para nueva cuenta {account_id}")
        else:
            logger.warning(f"⚠️ Error al programar insights para nueva cuenta {account_id}")
    
    async def remove_account_scheduled_tools(self, account_id: str):
        """
        Elimina herramientas programadas para una cuenta.
        
        Args:
            account_id: ID de la cuenta a eliminar
        """
        logger.info(f"Eliminando herramientas programadas para cuenta: {account_id}")
        
        # Cancelar insights diarios
        job_name = f"daily_daily_insights_{account_id}"
        success = tool_scheduler.cancel_scheduled_tool(job_name)
        
        if success:
            logger.info(f"✅ Herramientas programadas eliminadas para cuenta {account_id}")
        else:
            logger.warning(f"⚠️ No se encontraron herramientas programadas para cuenta {account_id}")
    
    def get_scheduled_tools_status(self) -> Dict[str, Any]:
        """
        Obtiene el estado de todas las herramientas programadas.
        
        Returns:
            Diccionario con el estado de las herramientas
        """
        return {
            "initialized": self.initialized,
            "scheduled_jobs": tool_scheduler.list_scheduled_tools(),
            "default_schedules": self.default_schedules
        }
    
    async def reschedule_tool(self, tool_name: str, new_time: time, account_id: Optional[str] = None):
        """
        Reprograma una herramienta existente.
        
        Args:
            tool_name: Nombre de la herramienta
            new_time: Nueva hora de ejecución
            account_id: ID de cuenta (opcional)
        """
        logger.info(f"Reprogramando herramienta '{tool_name}' para las {new_time}")
        
        # Cancelar job existente
        job_name = f"daily_{tool_name}_{account_id or 'all'}"
        tool_scheduler.cancel_scheduled_tool(job_name)
        
        # Reprogramar según el tipo de herramienta
        if tool_name == "daily_analysis":
            success = await schedule_daily_analysis(
                account_id=account_id,
                hour=new_time.hour,
                minute=new_time.minute
            )
        elif tool_name == "daily_insights":
            success = await schedule_daily_insights(
                account_id=account_id,
                hour=new_time.hour,
                minute=new_time.minute
            )
        else:
            logger.error(f"Tipo de herramienta desconocido: {tool_name}")
            return False
        
        if success:
            logger.info(f"✅ Herramienta '{tool_name}' reprogramada exitosamente")
        else:
            logger.error(f"❌ Error al reprogramar herramienta '{tool_name}'")
        
        return success


# Instancia global del gestor
scheduled_tools_manager = ScheduledToolsManager()


# Funciones de conveniencia
async def initialize_all_scheduled_tools():
    """Inicializa todas las herramientas programadas."""
    await scheduled_tools_manager.initialize_scheduled_tools()


async def add_scheduled_tools_for_account(account_id: str):
    """Agrega herramientas programadas para una nueva cuenta."""
    await scheduled_tools_manager.add_account_scheduled_tools(account_id)


async def remove_scheduled_tools_for_account(account_id: str):
    """Elimina herramientas programadas para una cuenta."""
    await scheduled_tools_manager.remove_account_scheduled_tools(account_id)


def get_scheduled_tools_status():
    """Obtiene el estado de las herramientas programadas."""
    return scheduled_tools_manager.get_scheduled_tools_status()
