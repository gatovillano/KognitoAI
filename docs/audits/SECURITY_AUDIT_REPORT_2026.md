# Informe de Auditoría de Seguridad - KognitoAI

**Fecha:** $(date +%Y-%m-%d)
**Agente Auditor:** KogniTerm

## Resumen Ejecutivo
Se ha realizado una auditoría estática y de configuración en el código base de KognitoAI. Se han identificado varias vulnerabilidades de severidad crítica y alta que deben ser abordadas antes de cualquier despliegue en producción.

## 1. Vulnerabilidades Críticas y Altas

### 1.1 Fuga de Credenciales (Crítica)
Se han encontrado archivos de credenciales JSON reales de cuentas de servicio de Google (`gen-lang-client-*.json`) dentro del directorio `credentials/`.
*   **Impacto:** Compromiso total de los recursos de Google Cloud asociados a esa cuenta de servicio.
*   **Remediación:** Eliminar los archivos del repositorio, revocar las credenciales actuales en Google Cloud y generar nuevas. Asegurar que `credentials/` esté en el `.gitignore`.

### 1.2 Vulnerabilidad XXE (XML External Entity) en CalDAV (Alta)
El archivo `api/caldav.py` (Línea 264) utiliza `xml.etree.ElementTree.fromstring` para parsear el cuerpo de las peticiones.
*   **Impacto:** Un atacante puede leer archivos locales del servidor o realizar SSRF (Server-Side Request Forgery).
*   **Remediación:** Sustituir `xml.etree.ElementTree` por la librería `defusedxml`.

### 1.3 Validación de Certificados SSL Desactivada (Alta)
En `api/onlyoffice.py` (Línea 1704), se realiza una petición HTTP asíncrona con `httpx.AsyncClient(verify=False)`.
*   **Impacto:** Permite ataques Man-in-the-Middle (MitM) interceptando y modificando el tráfico.
*   **Remediación:** Eliminar `verify=False` o apuntar a un certificado CA válido.

### 1.4 Base de Datos Neo4j Sin Autenticación (Crítica)
El archivo `docker-compose.yml` expone los puertos de Neo4j (7474 y 7687) y deshabilita explícitamente la autenticación (`NEO4J_AUTH: none`, `NEO4J_dbms_security_auth__enabled: "false"`).
*   **Impacto:** Cualquier usuario con acceso a la red puede leer, modificar o destruir el grafo de conocimiento.
*   **Remediación:** Configurar `NEO4J_AUTH: neo4j/contraseña_segura` y eliminar las directivas que deshabilitan la seguridad.

## 2. Vulnerabilidades de Severidad Media

### 2.1 Uso de Funciones Hash Débiles (MD5)
Múltiples archivos (`api/knowledge_graph.py`, `api/onlyoffice.py`, `core/agent.py`, `core/tts_manager.py`) utilizan `hashlib.md5()`.
*   **Remediación:** Si se usa para firmas o seguridad, cambiar a SHA-256. Si es solo para identificadores o caché, añadir `usedforsecurity=False` (en Python 3.9+).

### 2.2 Dependencias de Modelos Susceptibles a Supply Chain Attacks
En `core/reranker.py`, se descargan modelos desde Hugging Face usando `AutoTokenizer.from_pretrained()` sin especificar una revisión o hash.
*   **Remediación:** Anclar (`pin`) la versión del modelo usando el parámetro `revision="<commit_hash>"`.

### 2.3 Uso Inseguro de Directorios Temporales
Archivos como `api/main.py` y `core/config.py` hardcodean rutas en `/tmp` (ej. `/tmp/pollinations_images`).
*   **Remediación:** Utilizar el módulo `tempfile` de Python (`tempfile.gettempdir()` o `tempfile.TemporaryDirectory()`).

## 3. Plan de Acción Recomendado
1. Revocar las credenciales de Google Service Account expuestas.
2. Parchear la vulnerabilidad XXE en `api/caldav.py`.
3. Activar la autenticación en Neo4j y Redis en el `docker-compose.yml`.
4. Corregir el cliente HTTP en OnlyOffice para validar certificados SSL.

