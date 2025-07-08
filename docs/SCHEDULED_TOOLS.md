# Sistema de Herramientas Programadas - KognitoAI

## 📋 Descripción General

El sistema de herramientas programadas de KognitoAI permite ejecutar automáticamente herramientas específicas en intervalos de tiempo definidos. Esto es útil para tareas como análisis periódicos, generación de insights, limpieza de datos, y mantenimiento del sistema.

## 🚀 Características Principales

- **Programación Diaria**: Ejecutar herramientas todos los días a una hora específica
- **Programación Semanal**: Ejecutar herramientas una vez por semana en un día específico
- **Programación por Intervalo**: Ejecutar herramientas cada X horas
- **Gestión por Cuenta**: Programar herramientas específicas para cada usuario
- **Persistencia**: Las programaciones sobreviven a reinicios del sistema
- **Interfaz de Chat**: Los usuarios pueden gestionar programaciones desde Telegram

## 🛠️ Herramientas Disponibles

### 1. Análisis Diario (`daily_analysis`)
- **Descripción**: Ejecuta un análisis completo de la base de conocimiento
- **Recomendado**: Diariamente a las 2:00 AM
- **Función**: Analiza conexiones entre documentos, notas y conversaciones

### 2. Insights Diarios (`daily_insights`)
- **Descripción**: Genera insights proactivos basados en el conocimiento del usuario
- **Recomendado**: Diariamente a las 8:00 AM
- **Función**: Identifica patrones y sugiere conexiones relevantes

### 3. Limpieza Semanal (`weekly_cleanup`)
- **Descripción**: Limpia datos obsoletos y optimiza la base de datos
- **Recomendado**: Domingos a las 3:00 AM
- **Función**: Elimina análisis antiguos y optimiza el rendimiento

## 📅 Tipos de Programación

### Programación Diaria
```python
await tool_scheduler.schedule_daily_tool(
    tool_name="daily_analysis",
    tool_function=analysis_function,
    execution_time=time(hour=2, minute=0),
    account_id="user_123"
)
```

### Programación Semanal
```python
await tool_scheduler.schedule_weekly_tool(
    tool_name="weekly_cleanup",
    tool_function=cleanup_function,
    day_of_week=6,  # 0=Lunes, 6=Domingo
    execution_time=time(hour=3, minute=0),
    account_id="user_123"
)
```

### Programación por Intervalo
```python
await tool_scheduler.schedule_interval_tool(
    tool_name="interval_insights",
    tool_function=insights_function,
    interval_hours=6,
    account_id="user_123"
)
```

## 💬 Uso desde el Chat de Telegram

Los usuarios pueden gestionar sus herramientas programadas directamente desde el chat:

### Comandos de Ejemplo

**Programar análisis diario:**
```
"Programa un análisis diario de mi conocimiento todos los días a las 2:00 AM"
```

**Programar insights semanales:**
```
"Quiero que se generen insights proactivos todos los lunes a las 8:00 AM"
```

**Programar por intervalo:**
```
"Programa una limpieza de datos cada 12 horas"
```

**Ver herramientas programadas:**
```
"¿Qué herramientas tengo programadas?"
```

**Cancelar programación:**
```
"Cancela el análisis diario programado"
```

## 🔧 Configuración del Sistema

### Inicialización Automática

El sistema se inicializa automáticamente al arrancar la aplicación:

```python
# En run_telegram_bot.py
from utils.scheduled_tools_manager import initialize_all_scheduled_tools

# Durante el arranque
await initialize_all_scheduled_tools()
```

### Configuraciones por Defecto

```python
default_schedules = {
    "daily_analysis": {"hour": 2, "minute": 0},      # 2:00 AM
    "daily_insights": {"hour": 8, "minute": 0},      # 8:00 AM
    "weekly_cleanup": {"day": 6, "hour": 3, "minute": 0}  # Domingo 3:00 AM
}
```

## 👥 Perfiles de Usuario Recomendados

### Usuario Casual
- **Insights diarios**: 8:00 AM
- **Limpieza semanal**: Domingo 11:00 PM

### Usuario Profesional
- **Análisis diario**: 2:00 AM
- **Insights diarios**: 7:30 AM
- **Limpieza semanal**: Domingo 3:00 AM

### Usuario Intensivo
- **Análisis diario**: 1:00 AM
- **Insights cada 6 horas**: Continuo
- **Limpieza semanal**: Domingo 2:00 AM

## 🔍 Monitoreo y Gestión

### Listar Herramientas Programadas
```python
status = scheduled_tools_manager.get_scheduled_tools_status()
scheduled_jobs = tool_scheduler.list_scheduled_tools()
```

### Cancelar Herramientas
```python
success = tool_scheduler.cancel_scheduled_tool("job_name")
```

### Reprogramar Herramientas
```python
await scheduled_tools_manager.reschedule_tool(
    tool_name="daily_analysis",
    new_time=time(hour=3, minute=30),
    account_id="user_123"
)
```

## 🏗️ Arquitectura del Sistema

### Componentes Principales

1. **ToolScheduler** (`utils/tool_scheduler.py`)
   - Gestiona la programación individual de herramientas
   - Interfaz con JobQueue de Telegram

2. **ScheduledToolsManager** (`utils/scheduled_tools_manager.py`)
   - Gestión centralizada del sistema
   - Inicialización y configuración por defecto

3. **Herramientas de Chat** (`tools/schedule_tool_execution.py`)
   - `ScheduleToolExecutionTool`: Programar desde chat
   - `ListScheduledToolsTool`: Listar desde chat

### Flujo de Ejecución

1. **Inicialización**: Al arrancar la aplicación
2. **Programación**: Usuario programa herramientas via chat o código
3. **Ejecución**: JobQueue ejecuta herramientas en horarios programados
4. **Persistencia**: Programaciones se mantienen en memoria del JobQueue

## 🚨 Consideraciones Importantes

### Limitaciones
- Requiere que el bot de Telegram esté activo
- Las programaciones se pierden si el JobQueue no está disponible
- Máximo de herramientas programadas limitado por memoria

### Mejores Prácticas
- Programar herramientas intensivas en horarios de baja actividad
- Monitorear regularmente el estado de las programaciones
- Usar horarios escalonados para evitar sobrecarga del sistema

### Manejo de Errores
- Las herramientas fallan silenciosamente y se registran en logs
- Errores no afectan otras herramientas programadas
- Sistema robusto ante fallos individuales

## 🔮 Futuras Mejoras

### Próximas Características
- **Persistencia en Base de Datos**: Guardar programaciones en PostgreSQL
- **Interfaz Web**: Gestión visual desde el frontend
- **Notificaciones**: Alertas cuando las herramientas se ejecutan
- **Métricas**: Estadísticas de ejecución y rendimiento
- **Programación Condicional**: Ejecutar solo si se cumplen condiciones

### Integración con Celery
```python
# Futura implementación con Celery
from celery import Celery

app = Celery('kognito_scheduler')

@app.task
def scheduled_analysis_task(account_id):
    # Lógica de análisis
    pass

# Programación con Celery Beat
app.conf.beat_schedule = {
    'daily-analysis': {
        'task': 'scheduled_analysis_task',
        'schedule': crontab(hour=2, minute=0),
    },
}
```

## 📞 Soporte

Para problemas o preguntas sobre el sistema de herramientas programadas:

1. **Logs**: Revisar logs en `/var/log/kognito/`
2. **Estado**: Usar `get_scheduled_tools_status()`
3. **Reinicio**: Reiniciar el sistema si hay problemas persistentes

## 📚 Referencias

- [Documentación de python-telegram-bot JobQueue](https://docs.python-telegram-bot.org/en/stable/telegram.ext.jobqueue.html)
- [APScheduler Documentation](https://apscheduler.readthedocs.io/)
- [Celery Documentation](https://docs.celeryproject.org/)
