# Informe de Optimización de CPU para run_api.py en Contenedor kognito_core

## Fecha
21-01-2026

## Resumen Ejecutivo
El análisis del código fuente revela varias causas potenciales del alto uso de CPU (90-100%) observado en la ejecución de `run_api.py` dentro del contenedor `kognito_core`. Las principales causas identificadas incluyen la configuración de desarrollo de Uvicorn, la ejecución de herramientas programadas intensivas en CPU, el procesamiento de WebSockets para transcripción de audio, y la inicialización de múltiples modelos de IA. Se presentan propuestas detalladas para optimizar el rendimiento.

## Análisis de Causas Identificadas

### 1. Configuración de Uvicorn con Recarga Automática
**Causa:** Tanto en `run_api.py` como en `docker-compose.yml`, Uvicorn se ejecuta con `--reload` activado, lo que monitorea cambios en archivos y reinicia el servidor automáticamente.

**Impacto:** En entornos de desarrollo, esto puede consumir hasta el 100% de CPU debido al monitoreo continuo del sistema de archivos.

**Evidencia:**
- `run_api.py:40`: `uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)`
- `docker-compose.yml:37`: `command: uvicorn run_api:app --host 0.0.0.0 --port 8000 --reload`

### 2. Herramientas Programadas con Alto Consumo de CPU
**Causa:** El sistema utiliza APScheduler para ejecutar herramientas programadas que involucran llamadas a LLMs y procesamiento intensivo.

**Herramientas identificadas:**
- **Análisis diario global** (2:00 AM): `run_batch_analysis_job` - procesa grandes volúmenes de datos
- **Insights diarios por cuenta** (8:00 AM): `GetProactiveInsightsTool` - genera insights usando LLMs
- **Limpieza semanal** (Domingo 3:00 AM): Mantenimiento del sistema

**Impacto:** Con múltiples cuentas activas, estas tareas pueden ejecutarse simultáneamente, saturando la CPU.

**Evidencia:**
- `utils/scheduled_tools_manager.py`: Inicializa herramientas para cada cuenta activa
- `utils/tool_scheduler.py`: Usa BackgroundScheduler para ejecutar jobs

### 3. Procesamiento de WebSockets para Transcripción de Audio
**Causa:** El endpoint `/ws/audio/transcribe/{account_id}` carga el modelo Whisper y procesa audio en tiempo real.

**Impacto:** Cada conexión WebSocket activa consume CPU significativa para transcribir audio continuamente.

**Evidencia:**
- `api/main.py:210-252`: WebSocket para transcripción de audio
- `utils/audio_transcriber.py`: Contiene bucles `while True` para procesamiento continuo

### 4. Inicialización de Múltiples Modelos de IA
**Causa:** En el startup, se inicializan varios modelos pesados: LLM principal, LLM rápido, modelo de visión, embeddings y Whisper.

**Impacto:** La carga inicial y mantenimiento de estos modelos en memoria puede causar picos de CPU, especialmente si no están optimizados para GPU.

**Evidencia:**
- `api/main.py:117-147`: Startup event inicializa todos los modelos
- `core/llm_manager.py`: Inicializa instancias de ChatLiteLLM

### 5. Operaciones de Base de Datos y Grafos
**Causa:** Consultas frecuentes a PostgreSQL y Neo4j, especialmente en herramientas programadas y procesamiento de conocimiento.

**Impacto:** Consultas no optimizadas o falta de índices pueden causar alto uso de CPU.

## Propuestas de Optimización

### 1. Desactivar Recarga Automática en Producción
**Propuesta:** Modificar la configuración para deshabilitar `--reload` en entornos de producción.

**Implementación:**
```yaml
# docker-compose.yml
command: uvicorn run_api:app --host 0.0.0.0 --port 8000 --workers 4
```

**Beneficio:** Reduce el uso de CPU del 100% a niveles normales de operación.

### 2. Optimizar Herramientas Programadas
**Propuestas:**
- **Implementar procesamiento por lotes:** Agrupar análisis de múltiples cuentas en una sola ejecución
- **Ajustar frecuencias:** Reducir de diario a semanal para insights no críticos
- **Usar colas de trabajo:** Implementar Celery o similar para distribuir carga
- **Limitar concurrencia:** Máximo 2-3 jobs simultáneos

**Implementación:**
```python
# utils/scheduled_tools_manager.py
MAX_CONCURRENT_JOBS = 2
# Implementar semáforos para controlar concurrencia
```

### 3. Optimizar Procesamiento de Audio
**Propuestas:**
- **Limitar conexiones concurrentes:** Máximo 2-3 sesiones de transcripción simultáneas
- **Usar GPU para Whisper:** Configurar aceleración por hardware
- **Implementar buffering:** Procesar audio en chunks más grandes
- **Compresión de audio:** Reducir calidad para procesamiento más rápido

**Implementación:**
```python
# api/main.py
MAX_AUDIO_CONNECTIONS = 2
# Implementar contador de conexiones activas
```

### 4. Optimización de Modelos de IA
**Propuestas:**
- **Forzar uso de GPU:** Configurar LiteLLM para usar CUDA cuando esté disponible
- **Lazy loading:** Cargar modelos solo cuando sean necesarios
- **Pooling de modelos:** Reutilizar instancias en lugar de crear nuevas
- **Optimización de memoria:** Usar cuantización para modelos más ligeros

**Implementación:**
```python
# core/llm_manager.py
llm_kwargs["model_kwargs"] = {"device": "cuda" if torch.cuda.is_available() else "cpu"}
```

### 5. Optimizaciones de Base de Datos
**Propuestas:**
- **Implementar índices:** Agregar índices en consultas frecuentes
- **Usar conexiones async:** Aprovechar asyncpg para PostgreSQL
- **Implementar caching:** Redis para resultados de consultas comunes
- **Optimización de queries:** Revisar y optimizar queries complejas

### 6. Monitoreo y Profiling
**Propuestas:**
- **Implementar métricas:** Usar Prometheus para monitoreo de CPU
- **Profiling de código:** Usar `py-spy` o `cProfile` para identificar bottlenecks
- **Logs de rendimiento:** Agregar timing a operaciones críticas
- **Alertas automáticas:** Configurar alertas cuando CPU > 80%

### 7. Optimizaciones Arquitecturales
**Propuestas:**
- **Microservicios:** Separar procesamiento de audio en servicio dedicado
- **Load balancing:** Usar múltiples instancias del contenedor
- **Horizontal scaling:** Auto-scaling basado en carga de CPU
- **Async/await:** Asegurar que todas las operaciones I/O sean asíncronas

## Plan de Implementación Priorizado

### Fase 1: Crítico (Implementar inmediatamente)
1. Desactivar `--reload` en producción
2. Limitar conexiones de audio concurrentes
3. Optimizar configuración de GPU para modelos

### Fase 2: Alto Impacto (1-2 semanas)
1. Implementar concurrencia limitada en schedulers
2. Agregar índices de base de datos
3. Implementar caching básico

### Fase 3: Optimización Continua (1-2 meses)
1. Profiling detallado y optimización de código
2. Implementar métricas y monitoreo
3. Arquitectura de microservicios si es necesario

## Métricas de Éxito
- CPU promedio < 50% durante operación normal
- CPU < 80% durante picos de carga
- Tiempo de respuesta de API < 2 segundos
- Capacidad de manejar 10+ conexiones de audio simultáneas

## Riesgos y Consideraciones
- **Riesgo de downtime:** Cambios en configuración requieren reinicio del contenedor
- **Compatibilidad:** Verificar que optimizaciones de GPU no rompan funcionalidad
- **Costos:** Monitoreo adicional puede incrementar costos de infraestructura
- **Testing:** Requerir pruebas exhaustivas de carga antes de deploy

## Conclusión
El alto uso de CPU se debe principalmente a configuraciones de desarrollo y procesamiento intensivo de IA. Con las optimizaciones propuestas, se espera reducir significativamente el consumo de CPU mientras se mantiene la funcionalidad del sistema. Se recomienda implementar las mejoras de Fase 1 inmediatamente para alivio rápido, seguido de las fases posteriores para optimización continua.