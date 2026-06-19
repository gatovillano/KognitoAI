# Scripts de Visualización de Logs - KognitoAI

Scripts para monitorear y visualizar los logs del sistema KognitoAI en tiempo real.

## 📋 Índice de Scripts

| Script | Descripción |
|--------|-------------|
| [`view_core_logs.sh`](view_core_logs.sh) | Visualizador unificado de logs del core (backend + frontend + LLM) |
| [`monitor_llm_logs.py`](monitor_llm_logs.py) | Monitor específico de logs del LLM con formato detallado |

---

## 🚀 view_core_logs.sh

Visualizador de logs en tiempo real del core de KognitoAI con colores diferenciados y opciones de filtrado.

### Características

- ✅ **Visualización unificada**: Backend, frontend y LLM en una sola terminal
- ✅ **Colores diferenciados**: Verde (backend), azul (frontend), amarillo (LLM), magenta (herramientas)
- ✅ **Formato semántico**: Emojis para identificar tipos de logs (🚀 inicio, ✅ fin, 🔧 herramienta, ❌ error)
- ✅ **Detección automática**: Identifica servicios en ejecución por PID
- ✅ **Opciones de filtrado**: Por fuente, modo histórico, número de líneas

### Uso

```bash
# Ver todos los logs en tiempo real
./view_core_logs.sh

# Ver solo logs del backend
./view_core_logs.sh --backend

# Ver solo logs del frontend
./view_core_logs.sh --frontend

# Ver solo logs del LLM
./view_core_logs.sh --llm

# Ver historial de logs LLM (sin seguimiento en tiempo real)
./view_core_logs.sh --history

# Mostrar últimas 100 líneas de cada fuente
./view_core_logs.sh --tail 100

# Ver logs sin seguimiento en tiempo real
./view_core_logs.sh --no-follow
```

### Opciones

| Opción | Descripción |
|--------|-------------|
| `--backend` | Mostrar solo logs del backend (Python/Uvicorn) |
| `--frontend` | Mostrar solo logs del frontend (Next.js) |
| `--llm` | Mostrar solo logs del LLM |
| `--history` | Ver historial de archivos de log LLM |
| `--tail N` | Mostrar últimas N líneas (default: 50) |
| `--no-follow` | No seguir archivos en tiempo real |
| `-h, --help` | Mostrar ayuda |

### Ejemplos

```bash
# Monitorear solo el backend con 200 líneas iniciales
./view_core_logs.sh --backend --tail 200

# Ver el historial de logs LLM sin seguimiento
./view_core_logs.sh --history --no-follow

# Ver logs del LLM con 100 líneas iniciales
./view_core_logs.sh --llm --tail 100
```

### Estructura de Salida

```
╔══════════════════════════════════════════════════════════════════╗
║  📊 KognitoAI - Visualizador de Logs del Core                  ║
╚══════════════════════════════════════════════════════════════════╝

📈 ESTADÍSTICAS
──────────────────────────────────────────────────────────────
  Logs LLM totales:    92 archivos
  Backend:             ✓ Corriendo (PID: 1138397)
  Frontend:            ✓ Corriendo (PID: 1138410)

▶ BACKEND (Python/Uvicorn)
──────────────────────────────────────────────────────────────
✓ Backend detectado en ejecución (PID: 1138397)
  Mostrando últimas 50 líneas y siguiendo...

[BACKEND] INFO:     Uvicorn running on http://0.0.0.0:8889

▶ FRONTEND (Next.js)
──────────────────────────────────────────────────────────────
✓ Frontend detectado en ejecución (PID: 1138410)

[FRONTEND] GET / 200 in 45ms

▶ LLM LOGS (Comunicación con LLM)
──────────────────────────────────────────────────────────────
✓ Archivo de log más reciente: llm_detailed_20260520_015118.log

🚀 [LLM START] Processing user message...
📨 [PROMPT] User query: "¿Qué es KognitoAI?"
✅ [LLM END] Response generated in 2.3s
```

---

## 🔍 monitor_llm_logs.py

Monitor específico de logs del LLM con formateo detallado y seguimiento en tiempo real.

### Características

- ✅ Formateo específico para logs del LLM
- ✅ Detección automática del archivo de log más reciente
- ✅ Modo tail con número configurable de líneas
- ✅ Formato mejorado con emojis según tipo de log

### Uso

```bash
# Monitorear logs del LLM en tiempo real
python3 scripts/monitor_llm_logs.py

# Ver últimas 100 líneas sin seguimiento
python3 scripts/monitor_llm_logs.py --no-follow --lines 100

# Monitorear un archivo específico
python3 scripts/monitor_llm_logs.py --file logs/llm_detailed_20260520_015118.log
```

### Opciones

| Opción | Descripción |
|--------|-------------|
| `--file, -f` | Archivo de log específico a monitorear |
| `--lines, -n` | Número de líneas iniciales a mostrar (default: 50) |
| `--no-follow` | No seguir el archivo, solo mostrar líneas recientes |

---

## 📁 Ubicación de Logs

### Logs del LLM
```
logs/
├── llm_detailed_YYYYMMDD_HHMMSS.log  # Logs detallados del LLM
└── ...
```

### Logs del Backend
- Los logs de Uvicorn se muestran en stdout/stderr del proceso
- Para persistirlos en archivos, modificar `run_api.py` para usar `logging.FileHandler`

### Logs del Frontend
- Los logs de Next.js se muestran en stdout/stderr del proceso
- Next.js genera logs en `.next/` durante el build

---

## 🎨 Códigos de Color

| Fuente | Color | Código ANSI |
|--------|-------|-------------|
| Backend | Verde | `\033[0;32m` |
| Frontend | Azul | `\033[0;34m` |
| LLM | Amarillo | `\033[1;33m` |
| Herramientas | Magenta | `\033[0;35m` |
| Errores | Rojo | `\033[0;31m` |
| Info general | Cyan | `\033[0;36m` |

---

## 🔧 Requisitos

- **Shell**: Bash 4.0+ (para arrays y funciones)
- **Comandos**: `pgrep`, `tail`, `find`, `journalctl` (opcional)
- **Permisos**: Ejecutable (`chmod +x view_core_logs.sh`)

---

## 📝 Notas

- Los logs del backend y frontend se detectan por PID. Si los servicios no están en ejecución, se muestra un mensaje de advertencia.
- El script no interrumpe los servicios en ejecución. Solo lee sus logs.
- Para detener el seguimiento en tiempo real, presiona `Ctrl+C`.
- Los logs del LLM se guardan automáticamente en `logs/llm_detailed_*.log` por la configuración de `llm_logging_config.py`.
