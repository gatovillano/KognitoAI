# examples/scheduled_tools_examples.py

"""
Ejemplos de Uso del Sistema de Herramientas Programadas.

Este archivo contiene ejemplos de cómo usar el sistema de programación
de herramientas automáticas en KognitoAI.
"""

import asyncio
from datetime import time
from utils.tool_scheduler import tool_scheduler
from utils.scheduled_tools_manager import scheduled_tools_manager

async def example_schedule_daily_analysis():
    """
    Ejemplo: Programar análisis diario a las 2:00 AM.
    """
    print("📅 Ejemplo: Programando análisis diario...")
    
    async def daily_analysis_task(account_id: str = None, **kwargs):
        print(f"🔍 Ejecutando análisis diario para cuenta: {account_id or 'todas'}")
        # Aquí iría la lógica real del análisis
        return "Análisis completado"
    
    success = await tool_scheduler.schedule_daily_tool(
        tool_name="daily_analysis",
        tool_function=daily_analysis_task,
        execution_time=time(hour=2, minute=0),
        account_id="example_account_123"
    )
    
    if success:
        print("✅ Análisis diario programado exitosamente")
    else:
        print("❌ Error al programar análisis diario")

async def example_schedule_weekly_cleanup():
    """
    Ejemplo: Programar limpieza semanal los domingos a las 3:00 AM.
    """
    print("📅 Ejemplo: Programando limpieza semanal...")
    
    async def weekly_cleanup_task(account_id: str = None, **kwargs):
        print(f"🧹 Ejecutando limpieza semanal para cuenta: {account_id or 'todas'}")
        # Aquí iría la lógica real de limpieza
        return "Limpieza completada"
    
    success = await tool_scheduler.schedule_weekly_tool(
        tool_name="weekly_cleanup",
        tool_function=weekly_cleanup_task,
        day_of_week=6,  # Domingo
        execution_time=time(hour=3, minute=0),
        account_id="example_account_123"
    )
    
    if success:
        print("✅ Limpieza semanal programada exitosamente")
    else:
        print("❌ Error al programar limpieza semanal")

async def example_schedule_interval_insights():
    """
    Ejemplo: Programar insights cada 6 horas.
    """
    print("📅 Ejemplo: Programando insights cada 6 horas...")
    
    async def interval_insights_task(account_id: str = None, **kwargs):
        print(f"💡 Generando insights para cuenta: {account_id or 'todas'}")
        # Aquí iría la lógica real de generación de insights
        return "Insights generados"
    
    success = await tool_scheduler.schedule_interval_tool(
        tool_name="interval_insights",
        tool_function=interval_insights_task,
        interval_hours=6,
        account_id="example_account_123"
    )
    
    if success:
        print("✅ Insights por intervalo programados exitosamente")
    else:
        print("❌ Error al programar insights por intervalo")

async def example_list_scheduled_tools():
    """
    Ejemplo: Listar todas las herramientas programadas.
    """
    print("📋 Ejemplo: Listando herramientas programadas...")
    
    scheduled_jobs = tool_scheduler.list_scheduled_tools()
    
    if scheduled_jobs:
        print("📅 Herramientas programadas:")
        for job_name, job_info in scheduled_jobs.items():
            next_run = job_info.get("next_run")
            enabled = job_info.get("enabled", False)
            print(f"  - {job_name}: {'✅' if enabled else '❌'} Próxima: {next_run}")
    else:
        print("📭 No hay herramientas programadas")

async def example_cancel_scheduled_tool():
    """
    Ejemplo: Cancelar una herramienta programada.
    """
    print("🗑️ Ejemplo: Cancelando herramienta programada...")
    
    job_name = "daily_daily_analysis_example_account_123"
    success = tool_scheduler.cancel_scheduled_tool(job_name)
    
    if success:
        print(f"✅ Herramienta '{job_name}' cancelada exitosamente")
    else:
        print(f"❌ No se pudo cancelar la herramienta '{job_name}'")

async def example_get_system_status():
    """
    Ejemplo: Obtener estado del sistema de herramientas programadas.
    """
    print("📊 Ejemplo: Obteniendo estado del sistema...")
    
    status = scheduled_tools_manager.get_scheduled_tools_status()
    
    print(f"🔧 Sistema inicializado: {status.get('initialized', False)}")
    print(f"📅 Herramientas programadas: {len(status.get('scheduled_jobs', {}))}")
    print(f"⚙️ Configuraciones por defecto: {status.get('default_schedules', {})}")

async def run_all_examples():
    """
    Ejecuta todos los ejemplos.
    """
    print("🚀 Ejecutando ejemplos del sistema de herramientas programadas...\n")
    
    # Nota: Estos ejemplos requieren que el sistema de JobQueue esté disponible
    # En un entorno real, esto se ejecutaría dentro del contexto de la aplicación
    
    try:
        await example_schedule_daily_analysis()
        print()
        
        await example_schedule_weekly_cleanup()
        print()
        
        await example_schedule_interval_insights()
        print()
        
        await example_list_scheduled_tools()
        print()
        
        await example_get_system_status()
        print()
        
        await example_cancel_scheduled_tool()
        print()
        
        print("✅ Todos los ejemplos ejecutados exitosamente")
        
    except Exception as e:
        print(f"❌ Error en los ejemplos: {e}")

if __name__ == "__main__":
    # Ejecutar ejemplos
    asyncio.run(run_all_examples())


# Ejemplos de uso desde el chat de Telegram:

"""
Ejemplos de comandos que los usuarios pueden usar en el chat:

1. Programar análisis diario:
   "Programa un análisis diario de mi conocimiento todos los días a las 2:00 AM"
   
2. Programar insights semanales:
   "Quiero que se generen insights proactivos todos los lunes a las 8:00 AM"
   
3. Programar limpieza cada 12 horas:
   "Programa una limpieza de datos cada 12 horas"
   
4. Ver herramientas programadas:
   "¿Qué herramientas tengo programadas?"
   
5. Cancelar una herramienta:
   "Cancela el análisis diario programado"

El agente interpretará estos comandos y usará las herramientas correspondientes:
- schedule_tool_execution
- list_scheduled_tools
"""

# Configuraciones recomendadas por tipo de usuario:

RECOMMENDED_SCHEDULES = {
    "usuario_casual": {
        "daily_insights": {"hour": 8, "minute": 0},  # 8:00 AM
        "weekly_cleanup": {"day": 6, "hour": 23, "minute": 0}  # Domingo 11:00 PM
    },
    "usuario_profesional": {
        "daily_analysis": {"hour": 2, "minute": 0},  # 2:00 AM
        "daily_insights": {"hour": 7, "minute": 30},  # 7:30 AM
        "weekly_cleanup": {"day": 6, "hour": 3, "minute": 0}  # Domingo 3:00 AM
    },
    "usuario_intensivo": {
        "daily_analysis": {"hour": 1, "minute": 0},  # 1:00 AM
        "interval_insights": {"interval_hours": 6},  # Cada 6 horas
        "weekly_cleanup": {"day": 6, "hour": 2, "minute": 0}  # Domingo 2:00 AM
    }
}

async def setup_recommended_schedule(user_type: str, account_id: str):
    """
    Configura un horario recomendado según el tipo de usuario.
    
    Args:
        user_type: Tipo de usuario ('usuario_casual', 'usuario_profesional', 'usuario_intensivo')
        account_id: ID de la cuenta del usuario
    """
    if user_type not in RECOMMENDED_SCHEDULES:
        print(f"❌ Tipo de usuario '{user_type}' no reconocido")
        return
    
    schedule = RECOMMENDED_SCHEDULES[user_type]
    print(f"⚙️ Configurando horario recomendado para {user_type}...")
    
    for tool_name, config in schedule.items():
        if "interval_hours" in config:
            # Programación por intervalo
            await tool_scheduler.schedule_interval_tool(
                tool_name=tool_name,
                tool_function=lambda: print(f"Ejecutando {tool_name}"),
                interval_hours=config["interval_hours"],
                account_id=account_id
            )
        elif "day" in config:
            # Programación semanal
            await tool_scheduler.schedule_weekly_tool(
                tool_name=tool_name,
                tool_function=lambda: print(f"Ejecutando {tool_name}"),
                day_of_week=config["day"],
                execution_time=time(hour=config["hour"], minute=config["minute"]),
                account_id=account_id
            )
        else:
            # Programación diaria
            await tool_scheduler.schedule_daily_tool(
                tool_name=tool_name,
                tool_function=lambda: print(f"Ejecutando {tool_name}"),
                execution_time=time(hour=config["hour"], minute=config["minute"]),
                account_id=account_id
            )
    
    print(f"✅ Horario recomendado configurado para {user_type}")
