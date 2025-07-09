# 🔍 Scripts de Debugging del LLM

Esta carpeta contiene una suite completa de herramientas para monitorear y analizar exactamente cómo llegan los prompts al LLM en KognitoAI.

## 📋 Scripts Disponibles

### 1. 🛠️ `llm_debug_suite.py` - Suite Unificada
**Script principal que unifica todas las funcionalidades**

```bash
# Modo interactivo (recomendado para empezar)
python scripts/llm_debug_suite.py interactive

# Monitor en tiempo real
python scripts/llm_debug_suite.py monitor

# Análisis de estructura con estadísticas
python scripts/llm_debug_suite.py analyze --stats

# Solo estadísticas
python scripts/llm_debug_suite.py stats
```

### 2. 🔄 `detailed_llm_prompt_monitor.py` - Monitor en Tiempo Real
**Monitorea prompts y respuestas del LLM en tiempo real**

```bash
# Monitor básico
python scripts/detailed_llm_prompt_monitor.py

# Solo prompts (sin respuestas)
python scripts/detailed_llm_prompt_monitor.py --only-prompts

# Filtrar por usuario específico
python scripts/detailed_llm_prompt_monitor.py --account-id 12345

# Ver prompts completos sin truncar
python scripts/detailed_llm_prompt_monitor.py --no-truncate

# Guardar logs en archivo
python scripts/detailed_llm_prompt_monitor.py --save-to logs/detailed_prompts.log
```

### 3. 🔬 `prompt_structure_analyzer.py` - Analizador de Estructura
**Analiza la estructura y complejidad de los prompts**

```bash
# Análisis en tiempo real con estadísticas
python scripts/prompt_structure_analyzer.py --stats

# Analizar archivo de log específico
python scripts/prompt_structure_analyzer.py --log-file logs/llm.log --stats

# Exportar análisis a JSON
python scripts/prompt_structure_analyzer.py --export analysis.json --stats
```

## 🎯 Casos de Uso Principales

### 1. **Debugging de Prompts Mal Formateados**
```bash
# Ver estructura detallada de prompts
python scripts/llm_debug_suite.py analyze --stats
```

### 2. **Monitoreo de Sesión Específica**
```bash
# Filtrar por account_id
python scripts/llm_debug_suite.py monitor --account-id 12345
```

### 3. **Análisis de Rendimiento**
```bash
# Ver estadísticas de tokens y complejidad
python scripts/llm_debug_suite.py stats
```

### 4. **Debugging Interactivo**
```bash
# Modo interactivo con menú
python scripts/llm_debug_suite.py interactive
```

## 📊 Información que Muestran los Scripts

### Monitor en Tiempo Real (`detailed_llm_prompt_monitor.py`)
- ✅ **Prompts completos** enviados al LLM
- ✅ **Respuestas completas** del LLM
- ✅ **Herramientas ejecutadas** y sus parámetros
- ✅ **Información de tokens** (input/output/total)
- ✅ **Metadatos de sesión** (account_id, thread_id, modelo)
- ✅ **Timestamps** precisos
- ✅ **Filtrado por usuario**

### Analizador de Estructura (`prompt_structure_analyzer.py`)
- 🔬 **Desglose por secciones** del prompt
- 🔬 **Análisis de complejidad** (simple/moderado/complejo/muy_complejo)
- 🔬 **Componentes ReAct** detectados (Question/Thought/Action/Observation)
- 🔬 **Herramientas mencionadas** en el prompt
- 🔬 **Estadísticas de longitud** (caracteres, líneas, porcentajes)
- 🔬 **Tipos de mensaje** (System/Human/Assistant)
- 🔬 **Métricas globales** y tendencias

## 🚀 Inicio Rápido

### Para ver logs en tiempo real:
```bash
python scripts/llm_debug_suite.py monitor
```

### Para análisis detallado:
```bash
python scripts/llm_debug_suite.py analyze --stats
```

### Para modo interactivo:
```bash
python scripts/llm_debug_suite.py interactive
```

## 📈 Ejemplos de Salida

### Monitor en Tiempo Real
```
================================================================================
📤 PROMPT ENVIADO AL LLM 🕐 14:30:25
📋 Sesión: account_id: 12345 | thread_id: abc123 | model: gemini-2.5-flash
================================================================================
--- Sistema de Instrucciones ---
Eres un asistente de IA especializado en análisis de conocimiento...

--- Consulta Actual del Usuario ---
¿Puedes analizar mis notas sobre el proyecto X?

--- Herramientas Disponibles ---
knowledge_search_tool: Busca información en la base de conocimiento...
```

### Análisis de Estructura
```
🔬 ANÁLISIS DE PROMPT 🕐 14:30:25
📋 Sesión: account_id: 12345 | thread_id: abc123
================================================================================
📊 ESTADÍSTICAS GENERALES:
   • Longitud total: 2,847 caracteres
   • Líneas totales: 89
   • Secciones: 4
   • Herramientas mencionadas: 3

🎯 COMPLEJIDAD: MODERADO (Score: 3)
   Factores: Mediano (>1000 chars), Varias secciones (4), Con herramientas (3)

📑 SECCIONES DETECTADAS:
   1. Sistema de Instrucciones
      └─ 1,245 chars (43.7%) | 32 líneas
   2. Consulta Actual del Usuario
      └─ 156 chars (5.5%) | 3 líneas
   3. Herramientas Disponibles
      └─ 1,446 chars (50.8%) | 54 líneas
```

## ⚙️ Configuración

### Requisitos
- Python 3.8+
- Acceso a journalctl (para logs del sistema)
- KognitoAI ejecutándose con logging habilitado

### Variables de Entorno
Los scripts usan la configuración de logging existente de KognitoAI. Asegúrate de que:
- El logging del LLM esté habilitado
- Los logs se estén escribiendo a journalctl o archivos

### Permisos
```bash
# Hacer scripts ejecutables
chmod +x scripts/*.py

# Si necesitas acceso a journalctl sin sudo
sudo usermod -a -G systemd-journal $USER
```

## 🔧 Personalización

### Filtros Personalizados
Puedes modificar los scripts para añadir filtros adicionales:
- Por modelo específico
- Por tipo de herramienta
- Por longitud de prompt
- Por complejidad

### Formatos de Salida
Los scripts soportan:
- Salida a consola con colores
- Guardado en archivos de texto
- Exportación a JSON
- Integración con herramientas de análisis

## 🐛 Troubleshooting

### "No se encuentran logs"
```bash
# Verificar que KognitoAI esté ejecutándose
ps aux | grep kognito

# Verificar logs del sistema
journalctl -f | grep LLMCallback
```

### "Permisos denegados para journalctl"
```bash
# Añadir usuario al grupo systemd-journal
sudo usermod -a -G systemd-journal $USER
# Luego reiniciar sesión
```

### "Scripts no ejecutables"
```bash
chmod +x scripts/llm_debug_suite.py
chmod +x scripts/detailed_llm_prompt_monitor.py
chmod +x scripts/prompt_structure_analyzer.py
```

## 📝 Notas Importantes

1. **Rendimiento**: Los scripts están optimizados para no afectar el rendimiento de KognitoAI
2. **Privacidad**: Los logs pueden contener información sensible, úsalos responsablemente
3. **Almacenamiento**: Los logs pueden crecer rápidamente, considera rotación automática
4. **Tiempo Real**: Los scripts en tiempo real requieren que KognitoAI esté ejecutándose

## 🤝 Contribuir

Para añadir nuevas funcionalidades:
1. Modifica los scripts existentes
2. Añade nuevos filtros o análisis
3. Documenta los cambios en este README
4. Prueba con diferentes tipos de prompts

---

**💡 Tip**: Empieza con el modo interactivo (`python scripts/llm_debug_suite.py interactive`) para familiarizarte con las herramientas.
