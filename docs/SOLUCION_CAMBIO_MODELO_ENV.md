# Solución para Cambios en el Archivo .env No Aplicados

## 📋 Descripción del Problema

Cuando cambias el modelo LLM en el archivo `.env` y reinicias la aplicación, los cambios no se aplican y sigue apareciendo el modelo anterior.

## 🔍 Causa Raíz

El problema ocurre porque:

1. **El archivo `.env` se copia durante el build**: En el [`Dockerfile.core.hybrid`](../Dockerfile.core.hybrid:52), el archivo `.env` se copia al contenedor durante la construcción de la imagen Docker.

2. **No hay un volumen para el archivo `.env`**: En el [`docker-compose.yml`](../docker-compose.yml), los servicios `core`, `telegram_client` y `telegram_panel` no tienen un volumen que monte el archivo `.env` del host.

3. **Los cambios en el host no se reflejan**: Cuando cambias el archivo `.env` en el host, el contenedor sigue usando la versión copiada durante el build.

## ✅ Solución Implementada

He modificado el [`docker-compose.yml`](../docker-compose.yml) para agregar volúmenes que montan el archivo `.env` del host en los siguientes servicios:

- **core**: Línea 62
- **telegram_client**: Línea 105
- **telegram_panel**: Línea 162

```yaml
volumes:
  # ... otros volúmenes ...
  - ./.env:/app/.env:ro  # Montar el archivo .env para que los cambios se apliquen sin reconstruir
```

## 🚀 Cómo Aplicar los Cambios

### Opción 1: Usar el Script Automático (Recomendado)

He creado el script [`restart_core_with_new_env.sh`](../restart_core_with_new_env.sh) que automatiza el proceso:

```bash
./restart_core_with_new_env.sh
```

Este script:

1. Detiene el servicio `core`
2. Reconstruye el servicio `core` (copia el nuevo archivo `.env`)
3. Inicia el servicio `core`
4. Verifica que el servicio esté corriendo

### Opción 2: Manualmente

Si prefieres hacerlo manualmente:

```bash
# Detener el servicio core
docker-compose stop core

# Reconstruir el servicio core
docker-compose build core

# Iniciar el servicio core
docker-compose up -d core

# Verificar que el servicio esté corriendo
docker-compose ps core
```

### Opción 3: Solo Reiniciar (Después de la Solución)

Una vez que hayas aplicado la solución (los volúmenes en `docker-compose.yml`), en el futuro solo necesitarás reiniciar el servicio:

```bash
# Reiniciar el servicio core
docker-compose restart core
```

## 📝 Verificación

Para verificar que el cambio se ha aplicado correctamente, puedes revisar los logs del servicio `core`:

```bash
docker-compose logs -f core | grep "Initializing main agent LLM"
```

Deberías ver algo como:

```
🛠️ Initializing main agent LLM with rate limiting (LiteLLM - openrouter/openai/gpt-oss-120b:free)...
```

## 🎯 Configuración Actual

En el archivo [`.env`](../.env:34), el modelo está configurado como:

```env
LLM_MODEL="openrouter/openai/gpt-oss-120b:free"
FAST_LLM_MODEL="openrouter/openai/gpt-oss-120b:free"
```

## ⚠️ Notas Importantes

1. **Solo lectura**: El volumen está montado como `:ro` (read-only) para evitar que el contenedor modifique el archivo `.env` del host.

2. **Reinicio necesario**: Después de cambiar el archivo `.env`, siempre debes reiniciar el servicio `core` para que los cambios se apliquen.

3. **Otros servicios**: Si cambias configuraciones que afectan a otros servicios (como `telegram_client` o `telegram_panel`), también debes reiniciar esos servicios.

4. **Variables de entorno**: Las variables de entorno se leen al inicio de la aplicación. Si cambias una variable de entorno, debes reiniciar el servicio correspondiente.

## 🔧 Solución de Problemas

### Si los cambios aún no se aplican

1. **Verifica que el archivo `.env` se haya modificado correctamente**:

   ```bash
   cat .env | grep LLM_MODEL
   ```

2. **Verifica que el volumen esté montado correctamente**:

   ```bash
   docker-compose exec core ls -la /app/.env
   ```

3. **Reconstruye el contenedor**:

   ```bash
   docker-compose down
   docker-compose build core
   docker-compose up -d core
   ```

4. **Verifica los logs**:

   ```bash
   docker-compose logs core | grep "LLM"
   ```

## 📚 Referencias

- [`Dockerfile.core.hybrid`](../Dockerfile.core.hybrid) - Archivo de construcción del contenedor core
- [`docker-compose.yml`](../docker-compose.yml) - Configuración de Docker Compose
- [`.env`](../.env) - Archivo de variables de entorno
- [`core/config.py`](../core/config.py) - Módulo de configuración
- [`core/llm_manager.py`](../core/llm_manager.py) - Gestor de modelos LLM
