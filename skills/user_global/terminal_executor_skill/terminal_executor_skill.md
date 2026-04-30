# Terminal Executor Skill

Esta skill permite ejecutar comandos de terminal (shell) desde dentro del asistente y obtener su salida.

## Uso

Puedes invocar la skill de dos maneras:

### 1. A través de lenguaje natural (recomendado)
Simplemente pídele al asistente que ejecute un comando, por ejemplo:
- "¿Qué versión de Ollama está instalada?"
- "Muestra el contenido de `/tmp`"
- "Verifica si el puerto 11434 está escuchando"

El asistente decidirá automáticamente usar la skill `terminal_executor`.

### 2. Llamada directa a la herramienta
Si prefieres especificar la skill explícitamente, usa el formato:

```
LLAMADA_A_HERRAMIENTA: terminal_executor
{"command": "tu_comando_aqui", "timeout": 30}
```

#### Parámetros
- `command` (string, requerido): El comando de terminal que deseas ejecutar.
- `timeout` (integer, opcional): Número máximo de segundos que se permitirá la ejecución del comando. Por defecto es 30 segundos.

#### Salida
La skill devuelve un texto formateado que incluye:
- Código de retorno del proceso.
- STDOUT (si hay salida estándar).
- STDERR (si hay salida de error).
- Mensaje indicando si no hubo salida o si ocurrió un timeout/excepción.

## Ejemplos

| Objetivo | Comando | Qué hace |
|----------|---------|----------|
| Verificar procesos de Ollama | `ps aux | grep ollama` | Lista procesos que contengan "ollama". |
| Comprobar puerto 11434 | `ss -tlnp | grep :11434` | Muestra si algo está escuchando en ese puerto. |
| Probar API de Ollama | `curl -s http://localhost:11434` | Debería devolver `ollama is running`. |
| Listar modelos de Ollama | `ollama list` | Muestra los modelos descargados. |
| Ver espacio en disco | `df -h` | Muestra uso de sistemas de archivos legible. |

## Consideraciones de seguridad

- La skill ejecuta los comandos con los mismos privilegios que el proceso que ejecuta al asistente.
- Evita comandos destructivos (por ejemplo, `rm -rf /`, `dd if=/dev/zero of=/dev/sda`) a menos que estés absolutamente seguro.
- En entornos de producción o compartidos, considera crear una versión con lista blanca de comandos permitidos o envolverla en un contenedor con capacidades limitadas.
- El parámetro `timeout` ayuda a evitar que un comando se quede colgado indefinidamente.

## Notas

- La skill utiliza `subprocess.run` con `shell=True`, por lo que puedes usar tuberías, redirecciones y otras características de shell.
- Si el comando produce una salida muy grande, solo se devolverá lo que captura `subprocess.run` (limitado por la memoria disponible).