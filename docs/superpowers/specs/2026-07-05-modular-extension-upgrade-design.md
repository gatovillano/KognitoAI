# Especificación de Diseño: Mecanismo de Actualización Adaptativo para Extensiones Modulares

## Contexto y Problema
Kognito AI permite extender sus capacidades mediante módulos o extensiones independientes ubicadas en la carpeta git-ignored `extensions/`. Estas extensiones copian componentes al proyecto e inyectan importaciones y rutas en archivos centrales rastreados por Git (como `api/main.py` y `next.config.mjs`).

Cuando un usuario actualiza el sistema mediante `kognitoai upgrade` (que internamente ejecuta `git pull`), el comando falla si Git detecta modificaciones locales en los archivos rastreados, o bien sobreescribe las modificaciones de las extensiones dejándolas inoperativas.

## Solución Propuesta
Automatizar el ciclo de vida de las extensiones durante el proceso de actualización mediante un script ayudante (`scripts/upgrade_helper.py`) integrado en el comando `kognitoai upgrade` que realice lo siguiente:
1. **Pre-Upgrade**: Identifica qué extensiones están activas, persiste sus nombres en un archivo de estado y ejecuta su correspondiente desinstalación (`python extensions/<nombre>/install.py --uninstall`). Esto limpia el repositorio base.
2. **Git Pull**: El repositorio de Kognito AI se actualiza limpiamente sin conflictos.
3. **Post-Upgrade**: Lee el archivo de estado y vuelve a ejecutar la instalación de las extensiones previamente activas (`python extensions/<nombre>/install.py`).

## Arquitectura y Componentes

### 1. Script Ayudante: `scripts/upgrade_helper.py`
El script contiene la lógica para gestionar las extensiones. 
- **Directorio de Extensiones**: `extensions/` (ubicado dentro de la raíz del repositorio de Kognito AI).
- **Archivo de Estado**: `/home/gato/.kognito/config/active_extensions.json` (o ruta relativa al directorio `.kognito` del usuario).
- **Heurística de Detección**: Una extensión se considera instalada si tiene una carpeta del mismo nombre dentro de `api/` (ej. `api/gallery_selection_panel`).

### 2. Modificaciones en el CLI `kognitoai`
Se modificará la función `cmd_upgrade()` en `kognitoai` para invocar los hooks correspondientes en caso de que el script helper exista.

## Plan de Verificación

### Pruebas Manuales
1. Instalar la extensión `gallery_selection_panel` manualmente.
2. Comprobar que `api/main.py` y otros archivos tengan los cambios aplicados.
3. Ejecutar `kognitoai upgrade`.
4. Verificar que se realice la desinstalación temporal, la actualización y la posterior reinstalación de forma exitosa y automática.
