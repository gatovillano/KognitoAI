# Guía de Logging Detallado del LLM

Esta guía explica cómo usar el sistema de logging detallado implementado para capturar toda la comunicación con el LLM.

## 🎯 Objetivo

El sistema de logging detallado permite ver exactamente:
- Qué prompts se envían al LLM
- Qué respuestas recibe el sistema
- Qué herramientas se ejecutan
- Todos los pasos intermedios del agente
- Metadatos y configuración del LLM

## 📁 Archivos de Log

Los logs se guardan en el directorio `logs/` con el formato:
```
logs/llm_detailed_YYYYMMDD_HHMMSS.log
```

Ejemplo: `logs/llm_detailed_20250106_143022.log`

## 🔧 Configuración

### Automática
El logging detallado se activa automáticamente cuando se inicia la aplicación. La configuración está en:
- `api/main.py` - Configuración principal
- `utils/llm_logging_config.py` - Configuración específica del LLM

### Manual
Para configurar manualmente:

```python
from utils.llm_logging_config import setup_llm_detailed_logging, enable_verbose_langchain_logging

# Configurar logging básico
setup_llm_detailed_logging(log_level="DEBUG", log_file="logs/mi_log.log")

# Habilitar logging muy detallado
enable_verbose_langchain_logging()
```

## 📊 Monitoreo en Tiempo Real

### Script de Línea de Comandos

```bash
# Monitorear el log más reciente
python scripts/monitor_llm_logs.py

# Monitorear un archivo específico
python scripts/monitor_llm_logs.py -f logs/llm_detailed_20250106_143022.log

# Mostrar solo las últimas 20 líneas sin seguimiento
python scripts/monitor_llm_logs.py -n 20 --no-follow
```

### API Endpoints

#### Listar archivos de log
```http
GET /api/logs/llm/files
```

#### Obtener contenido de log
```http
GET /api/logs/llm/content?filename=llm_detailed_20250106_143022.log&lines=100
```

#### Stream en tiempo real
```http
GET /api/logs/llm/stream?filename=llm_detailed_20250106_143022.log
```

#### Buscar en logs
```http
GET /api/logs/llm/search?query=PROMPT&filename=llm_detailed_20250106_143022.log
```

## 📝 Formato de Logs

### Tipos de Entradas

#### 🚀 Inicio de LLM
```
🚀 [LLM START] Account: abc123, Thread: def456
📝 [LLM INPUT] Serialized LLM: {...}
```

#### 💬 Inicio de Modelo de Chat
```
💬 [CHAT MODEL START] Account: abc123, Thread: def456
📦 [MESSAGE BATCH 1]
📧 [MESSAGE 1] Type: SystemMessage
📄 [CONTENT]:
--------------------------------------------------------------------------------
Eres un asistente de IA...
--------------------------------------------------------------------------------
```

#### 📨 Prompts y Mensajes
```
📨 [PROMPT 1] Content:
--------------------------------------------------------------------------------
¿Cuál es la capital de Francia?
--------------------------------------------------------------------------------
```

#### 📤 Respuestas del LLM
```
✅ [LLM END] Account: abc123, Thread: def456
📤 [RESPONSE 1.1]:
--------------------------------------------------------------------------------
La capital de Francia es París...
--------------------------------------------------------------------------------
```

#### 🔧 Ejecución de Herramientas
```
🔧 [TOOL START] web_search - Account: abc123, Thread: def456
🔨 [TOOL INPUT]:
--------------------------------------------------------------------------------
{"query": "capital de Francia"}
--------------------------------------------------------------------------------
✅ [TOOL END] Account: abc123, Thread: def456
🔧 [TOOL OUTPUT]:
--------------------------------------------------------------------------------
París es la capital y ciudad más poblada de Francia...
--------------------------------------------------------------------------------
```

#### 🎯 Input del Agente
```
🎯 [AGENT INPUT] Account: abc123, Thread: def456
📋 [INPUT DATA]:
--------------------------------------------------------------------------------
User Message: ¿Cuál es la capital de Francia?
Chat History Length: 3 messages
  [1] SystemMessage: Eres un asistente de IA...
  [2] HumanMessage: Hola
  [3] AIMessage: ¡Hola! ¿En qué puedo ayudarte?
--------------------------------------------------------------------------------
```

## 🔍 Análisis de Logs

### Buscar Comunicaciones Específicas

Para encontrar toda la comunicación de una conversación específica:
```bash
grep "Account: abc123, Thread: def456" logs/llm_detailed_*.log
```

### Filtrar por Tipo de Evento

```bash
# Solo inicios de LLM
grep "LLM START" logs/llm_detailed_*.log

# Solo respuestas
grep "RESPONSE" logs/llm_detailed_*.log

# Solo ejecución de herramientas
grep "TOOL START\|TOOL END" logs/llm_detailed_*.log
```

### Extraer Prompts Completos

```bash
# Extraer todos los prompts enviados
grep -A 10 "CONTENT]:" logs/llm_detailed_*.log
```

## 🛠️ Debugging

### Problemas Comunes

1. **No se generan logs**
   - Verificar que el directorio `logs/` existe
   - Comprobar permisos de escritura
   - Revisar configuración de logging

2. **Logs muy grandes**
   - Los logs pueden crecer rápidamente
   - Considerar rotación de logs
   - Filtrar por nivel de log

3. **Rendimiento**
   - El logging detallado puede afectar el rendimiento
   - Usar solo para debugging
   - Desactivar en producción si es necesario

### Configuración de Producción

Para producción, considera:

```python
# Logging menos verbose
setup_llm_detailed_logging(log_level="INFO")

# Sin archivo de log (solo consola)
setup_llm_detailed_logging(log_level="INFO", log_file=None)
```

## 📈 Métricas y Análisis

### Tiempo de Respuesta
Los logs incluyen timestamps precisos para analizar:
- Tiempo de procesamiento del LLM
- Tiempo de ejecución de herramientas
- Latencia total de respuesta

### Uso de Herramientas
Analizar qué herramientas se usan más frecuentemente:
```bash
grep "TOOL START" logs/llm_detailed_*.log | cut -d' ' -f8 | sort | uniq -c
```

### Errores
Identificar errores comunes:
```bash
grep "ERROR\|FATAL" logs/llm_detailed_*.log
```

## 🔒 Seguridad y Privacidad

⚠️ **IMPORTANTE**: Los logs contienen:
- Mensajes completos de usuarios
- Respuestas del LLM
- Datos potencialmente sensibles

**Recomendaciones**:
- No compartir logs sin revisar el contenido
- Implementar rotación y limpieza automática
- Considerar encriptación para logs en producción
- Cumplir con regulaciones de privacidad (GDPR, etc.)

## 🚀 Próximos Pasos

1. **Interfaz Web**: Crear una interfaz web para visualizar logs
2. **Alertas**: Configurar alertas para errores críticos
3. **Métricas**: Implementar dashboard de métricas
4. **Filtros Avanzados**: Añadir filtros más sofisticados
5. **Exportación**: Permitir exportar logs en diferentes formatos
