# 📊 Sistema de Logging Detallado del LLM - Implementación Completada

## ✅ ¿Qué se ha implementado?

Hemos implementado un sistema completo de logging detallado que captura **exactamente lo que recibe el LLM en cada mensaje**. El sistema incluye:

### 1. 🔧 Callback Personalizado (`DetailedLLMLoggingCallback`)
- **Ubicación**: `core/agent.py` (líneas 67-143)
- **Función**: Captura toda la comunicación con el LLM de manera estructurada
- **Características**:
  - Evita duplicación de logs
  - Trunca contenido muy largo para mantener legibilidad
  - Muestra información esencial: prompts, respuestas, herramientas, tokens

### 2. 📁 Sistema de Archivos de Log
- **Directorio**: `logs/`
- **Formato**: `llm_detailed_YYYYMMDD_HHMMSS.log`
- **Configuración**: `utils/llm_logging_config.py`

### 3. 🖥️ Script de Monitoreo en Tiempo Real
- **Archivo**: `scripts/monitor_llm_logs.py`
- **Función**: Permite ver los logs en tiempo real desde la línea de comandos

### 4. 🌐 API Endpoints para Logs
- **Archivo**: `api/logs.py`
- **Endpoints**:
  - `GET /api/logs/llm/files` - Lista archivos de log
  - `GET /api/logs/llm/content` - Obtiene contenido de logs
  - `GET /api/logs/llm/stream` - Stream en tiempo real
  - `GET /api/logs/llm/search` - Buscar en logs

## 🚀 Cómo usar el sistema

### Opción 1: Ver logs en tiempo real (Línea de comandos)
```bash
# Monitorear el log más reciente
python scripts/monitor_llm_logs.py

# Monitorear archivo específico
python scripts/monitor_llm_logs.py -f logs/llm_detailed_20250106_143022.log

# Ver solo las últimas 20 líneas
python scripts/monitor_llm_logs.py -n 20 --no-follow
```

### Opción 2: Ver logs en el contenedor Docker
```bash
# Entrar al contenedor
docker exec -it kognito_core bash

# Ver logs en tiempo real
python scripts/monitor_llm_logs.py

# O ver logs directamente
tail -f logs/llm_detailed_*.log
```

### Opción 3: Usar la API desde el frontend
```javascript
// Obtener archivos de log disponibles
fetch('/api/logs/llm/files')

// Obtener contenido de log
fetch('/api/logs/llm/content?lines=100')

// Stream en tiempo real
const eventSource = new EventSource('/api/logs/llm/stream');
eventSource.onmessage = (event) => {
    const logEntry = JSON.parse(event.data);
    console.log(logEntry);
};
```

## 📝 Formato de los Logs

### Ejemplo de salida típica:
```
2025-07-06 23:49:12,067 - LLMCallback - INFO - 💬 [CHAT START] Session: abc12345...def67890 | Model: gemini-2.0-flash | Messages: 35
2025-07-06 23:49:12,067 - LLMCallback - INFO - 📧 [USER INPUT] HumanMessage: ¿Cuál es la capital de Francia?
2025-07-06 23:49:12,068 - LLMCallback - INFO - ✅ [LLM END] Session: abc12345...def67890
2025-07-06 23:49:12,068 - LLMCallback - INFO - 📤 [LLM RESPONSE]: La capital de Francia es París, una ciudad histórica...
2025-07-06 23:49:12,068 - LLMCallback - INFO - 🔧 [TOKENS]: {'input_tokens': 150, 'output_tokens': 45}
```

### Tipos de eventos capturados:
- 💬 **[CHAT START]** - Inicio de procesamiento del LLM
- 📧 **[USER INPUT]** - Mensaje del usuario enviado al LLM
- 📤 **[LLM RESPONSE]** - Respuesta generada por el LLM
- 🔧 **[TOOL START]** - Inicio de ejecución de herramienta
- 🔨 **[TOOL INPUT]** - Input enviado a la herramienta
- ✅ **[TOOL END]** - Fin de ejecución de herramienta
- 🔧 **[TOOL OUTPUT]** - Output de la herramienta
- 🔧 **[TOKENS]** - Información de uso de tokens

## 🔍 Información capturada

El sistema captura **exactamente**:

1. **Prompts completos** enviados al LLM
2. **Historial de conversación** incluido en cada request
3. **Respuestas completas** del LLM
4. **Herramientas ejecutadas** y sus inputs/outputs
5. **Metadatos** como uso de tokens, modelo utilizado
6. **Información de sesión** (account_id, thread_id)

## 🛠️ Configuración actual

### Logging automático activado en:
- `api/main.py` - Configuración principal
- `core/agent.py` - Callback integrado en el agente
- `api/chat.py` - Callback en streaming

### Configuración de niveles:
- **LLMCallback**: INFO (nuestros logs personalizados)
- **core.agent**: INFO (logs del agente)
- **langchain**: WARNING (solo errores)

## 🎯 Próximos pasos sugeridos

1. **Probar el sistema**: Envía algunos mensajes y verifica que los logs se generen
2. **Monitorear en tiempo real**: Usa el script para ver la comunicación en vivo
3. **Analizar logs**: Busca patrones o problemas en la comunicación
4. **Optimizar si es necesario**: Ajusta el nivel de detalle según tus necesidades

## 📋 Comandos útiles

```bash
# Ver logs más recientes
ls -la logs/

# Buscar en logs
grep "USER INPUT" logs/llm_detailed_*.log

# Contar mensajes procesados
grep "CHAT START" logs/llm_detailed_*.log | wc -l

# Ver solo respuestas del LLM
grep "LLM RESPONSE" logs/llm_detailed_*.log
```

## ⚠️ Consideraciones importantes

1. **Privacidad**: Los logs contienen mensajes completos de usuarios
2. **Espacio**: Los logs pueden crecer rápidamente
3. **Rendimiento**: El logging detallado puede afectar ligeramente el rendimiento
4. **Rotación**: Considera implementar rotación automática de logs

¡El sistema está listo para usar! 🎉
