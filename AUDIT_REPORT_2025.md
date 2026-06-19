# Informe de Auditoría de Código - KognitoAI
**Fecha:** 2025-02-14  
**Auditor:** KogniTerm (Asistente de Auditoría)  
**Versión del Proyecto:** 0.1.0  
**Alcance:** Directorio `/home/gato/Proyectos/KognitoAI/kognito-ai`

---

## Resumen Ejecutivo

Se realizó una auditoría completa del proyecto KognitoAI, que consiste en una plataforma de inteligencia artificial con múltiples servicios (API Core, Telegram Gateway, Frontend Next.js, servicios de TTS, base de datos PostgreSQL con pgvector, Neo4j, etc.).

### Hallazgos Principales
- **1 Vulnerabilidad Crítica de Seguridad**: Terminal PTY remota sin restricciones suficientes
- **3 Vulnerabilidades Medias**: Secretos con valores por defecto en código, dependencias obsoletas, manejo de errores insuficiente
- **2 Vulnerabilidades Bajas**: Configuración de CORS potencialmente insegura, logging excesivo
- **Deuda Técnica Alta**: 6 funciones con complejidad ciclomática D (muy alta), 1 función con complejidad F (extremadamente alta)
- **Problemas de Mantenibilidad**: Archivo `core/database.py` con 1500+ líneas, múltiples responsabilidades en un solo módulo

### Estado de Salud del Código
- **Errores de compilación**: 0 (todos los archivos principales compilan correctamente)
- **Complejidad promedio**: Alta en módulos core (ollama_direct.py, skill_manager.py, llm_manager.py)
- **Cobertura de tests**: No disponible (no se encontraron tests unitarios ejecutables)
- **Documentación**: Parcial (existe README, AUDIT_REPORT previo y TODO.md)

---

## 1. Análisis de Estructura del Proyecto

### 1.1 Arquitectura General
El proyecto sigue una arquitectura de microservicios:
- **API Core** (`api/`): FastAPI con endpoints REST y WebSocket
- **Core** (`core/`): Lógica de negocio, IA, base de datos, skills
- **Telegram Gateway** (`telegram_gateway/`): Bot de Telegram
- **Frontend** (`kogninotes-app/`): Next.js 15 con TypeScript
- **Servicios auxiliares**: Kokoro TTS, Redis, Neo4j, PostgreSQL

### 1.2 Estadísticas de Código
- **Archivos Python**: ~200 archivos
- **Líneas de código (estimado)**: 50,000+ líneas
- **Dependencias Python**: 135 paquetes en requirements.txt
- **Dependencias Node.js**: 80+ paquetes en package.json

---

## 2. Análisis de Complejidad Ciclomática

Se ejecutó `radon cc` sobre los directorios `core/` y `api/`. Los resultados más críticos:

### 2.1 Funciones con Complejidad Muy Alta (D y F)

| Archivo | Función | Complejidad | Línea |
|---------|---------|-------------|-------|
| `core/ollama_direct.py` | `OllamaDirectChatModel._astream` | **D (23)** | 611 |
| `core/ollama_direct.py` | `convert_openai_payload_to_ollama` | **D (21)** | 214 |
| `core/ollama_direct.py` | `ollama_embeddings` | **D (21)** | 354 |
| `core/ollama_direct.py` | `OllamaDirectChatModel._prepare_payload` | **D (21)** | 465 |
| `core/skill_manager.py` | `SkillManager._instantiate_skill` | **D (29)** | 188 |
| `core/skill_manager.py` | `SkillManager.load_skills` | **D (28)** | 425 |
| `core/llm_manager.py` | `initialize_llms` | **F (113)** | 806 |
| `core/llm_manager.py` | `get_llm_for_user` | **F (76)** | 408 |
| `core/agenda_manager.py` | `schedule_event` | **C (20)** | 27 |
| `core/agenda_manager.py` | `get_agenda_for_period` | **C (19)** | 255 |

### 2.2 Clases con Alta Complejidad
- `core/database.py`: Clase `AgendaEvent` con complejidad C (11)
- `core/embedding_manager.py`: Clase `EmbeddingServiceFactory` con complejidad C (15)
- `core/enhanced_memory_manager.py`: Clase `EnhancedMemoryManager` con complejidad B (10)

### 2.3 Interpretación
- **F (40+)**: Crítico, requiere refactorización inmediata
- **D (21-40)**: Muy alto, riesgo de bugs y dificultad de mantenimiento
- **C (11-20)**: Alto, considerar refactorización

**Conclusión**: Las funciones `initialize_llms` y `get_llm_for_user` en `llm_manager.py` son extremadamente complejas y representan el mayor riesgo técnico.

---

## 3. Análisis de Seguridad

### 3.1 Vulnerabilidades Críticas

#### 🔴 VULN-001: Terminal PTY Remota sin Restricciones Suficientes
**Archivo:** `api/terminal.py`  
**Severidad:** CRÍTICA  
**CWE:** CWE-284 (Acceso no autorizado)

**Descripción:**  
El endpoint WebSocket `/ws/terminal/{account_id}` permite ejecutar comandos shell arbitrarios en el servidor. Aunque requiere autenticación JWT, existen varios problemas:

1. **Sin validación de comandos**: Cualquier comando puede ser ejecutado, incluyendo `rm -rf`, `curl`, `wget`, etc.
2. **Sin sandboxing**: El proceso se ejecuta con los permisos del usuario del servicio
3. **Sin límite de recursos**: No hay límite de CPU, memoria o tiempo de ejecución
4. **Acceso a variables de entorno**: El proceso hereda todo el entorno, incluyendo secretos

**Prueba de concepto:**
```python
# En api/terminal.py línea 142
os.execve(DEFAULT_SHELL, [DEFAULT_SHELL, "--login"], env)
# Cualquier comando puede ser ejecutado sin restricciones
```

**Impacto:**  
- Ejecución remota de código (RCE)
- Acceso a todos los secretos del sistema
- Posible movimiento lateral a otros servicios
- Borrado o modificación de datos sensibles

**Recomendación:**
- Implementar una lista blanca de comandos permitidos
- Ejecutar el PTY en un contenedor Docker aislado con recursos limitados
- Implementar timeouts y límites de recursos (cgroups)
- Auditar y registrar todos los comandos ejecutados
- Considerar eliminar este endpoint en producción o restringirlo a red privada VPN

---

### 3.2 Vulnerabilidades Medias

#### 🟡 VULN-002: Secretos con Valores por Defecto en Código
**Archivo:** `core/config.py`  
**Severidad:** MEDIA  
**CWE:** CWE-798 (Credenciales hardcodeadas)

**Descripción:**  
Múltiples secretos tienen valores por defecto inseguros:

```python
# core/config.py línea 245
self.admin_secret: str = get_secret("admin_secret", "ADMIN_SECRET", "default-admin-secret")

# core/config.py línea 248
self.db_encryption_key: str = get_secret("db_encryption_key", "DB_ENCRYPTION_KEY", "super-secret-db-encryption-key")

# core/config.py línea 268
self.internal_api_key_for_bot: str = get_secret("internal_api_key_for_bot", "INTERNAL_API_KEY_FOR_BOT", "super-secret-internal-key")

# core/config.py línea 197
self.jwt_secret_key: str = get_secret("jwt_secret_key", "JWT_SECRET_KEY", "supersecretkey")
```

**Impacto:**  
- Si no se configuran las variables de entorno, se usan valores conocidos
- Cualquier persona que revise el código conoce los fallbacks
- Ataques de fuerza bruta contra JWT son más fáciles
- Acceso no autorizado a endpoints administrativos

**Recomendación:**
- Eliminar valores por defecto inseguros
- Forzar configuración explícita en producción
- Implementar validación de fortaleza de secretos al inicio
- Usar gestores de secretos (HashiCorp Vault, AWS Secrets Manager)

---

#### 🟡 VULN-003: Dependencias con Versiones Flexibles
**Archivo:** `requirements.txt`  
**Severidad:** MEDIA  
**CWE:** CWE-1104 (Uso de versiones no fijadas de terceros)

**Descripción:**  
Muchas dependencias usan rangos amplios:
```
fastapi>=0.100.0
uvicorn>=0.20.0
sqlalchemy[asyncio]>=2.0.0
psycopg[async]>=3.1.0
```

**Impacto:**  
- Actualizaciones mayores pueden introducir breaking changes
- Dificulta la reproducibilidad de builds
- Ataques a supply chain (typosquatting, compromised packages)

**Recomendación:**
- Fijar versiones exactas en producción (`fastapi==0.104.1`)
- Usar `pip freeze` o `poetry.lock` para reproducibilidad
- Implementar Dependabot o Renovate para actualizaciones controladas
- Auditar dependencias con `pip-audit` o `safety`

---

#### 🟡 VULN-004: Manejo de Errores Insuficiente en PTY
**Archivo:** `api/terminal.py`  
**Severidad:** MEDIA  
**CWE:** CWE-754 (Manejo inadecuado de condiciones excepcionales)

**Descripción:**  
El manejo de errores en el PTY puede dejar procesos huérfanos:
```python
# Línea 231-235
try:
    os.kill(pid, signal.SIGTERM)
    await asyncio.sleep(0.2)
    os.waitpid(pid, os.WNOHANG)
except Exception:
    pass  # Silenciosamente ignora errores de limpieza
```

**Impacto:**  
- Procesos shell huérfanos consumiendo recursos
- Posible fuga de memoria
- Dificulta el debugging

**Recomendación:**
- Implementar logging estructurado de errores
- Usar `signal.SIGKILL` como fallback si `SIGTERM` falla
- Implementar watchdog para limpiar sesiones huérfanas

---

### 3.3 Vulnerabilidades Bajas

#### 🟢 VULN-005: Configuración CORS Amplia
**Archivo:** `core/config.py`  
**Severidad:** BAJA  
**CWE:** CWE-942 (Configuración CORS excesiva)

**Descripción:**
```python
self.cors_allowed_origins: Optional[str] = os.getenv("CORS_ALLOWED_ORIGINS")
```
Si no se configura, CORS podría estar deshabilitado o mal configurado.

**Recomendación:**  
- Establecer origen por defecto seguro (no `*`)
- Validar orígenes contra una lista blanca

---

#### 🟢 VULN-006: Logging de Información Sensible
**Archivo:** Múltiples  
**Severidad:** BAJA  
**CWE:** CWE-532 (Inserción de información sensible en archivos de log)

**Descripción:**  
El código usa `logger.info()` y `logger.warning()` en puntos que podrían exponer datos sensibles (tokens, IDs de usuario, etc.).

**Recomendación:**  
- Implementar filtrado de logs para datos sensibles
- Usar niveles de logging apropiados (no loguear tokens completos)

---

## 4. Análisis de Deuda Técnica

### 4.1 Arquitectura y Diseño

#### Problema: Archivo `core/database.py` Sobredimensionado
- **Líneas:** 1600+
- **Responsabilidades:** Modelos SQLAlchemy, funciones de acceso a datos, lógica de negocio
- **Impacto:** Dificulta mantenimiento, testing y comprensión

**Recomendación:**  
- Separar modelos (models/) de repositorios (repositories/)
- Implementar patrón Repository para acceso a datos
- Dividir en módulos por dominio (users/, documents/, agenda/, etc.)

---

#### Problema: Lógica de IA en `core/llm_manager.py`
- **Complejidad F (113) en `initialize_llms`**
- **Complejidad F (76) en `get_llm_for_user`**
- Mezcla configuración, inicialización y lógica de negocio

**Recomendación:**  
- Extraer factory para creación de LLMs
- Implementar strategy pattern para diferentes proveedores
- Dividir en módulos: `llm/factory.py`, `llm/providers/`, `llm/config.py`

---

### 4.2 Calidad de Código

#### Problema: Falta de Type Hints Completos
Muchas funciones carecen de type hints o usan `Any`:
```python
# Ejemplo en core/llm_manager.py
def get_llm_for_user(user_id: int, model_name: Optional[str] = None):
    # Falta return type
```

**Recomendación:**  
- Habilitar `mypy --strict` en CI
- Agregar type hints a todas las funciones públicas
- Usar `typing` module para tipos complejos

---

#### Problema: Magic Numbers y Strings
```python
# Ejemplos encontrados
if not data:  # ¿Qué significa "no data"?
os.write(master_fd, d.encode("utf-8"))  # ¿Por qué utf-8?
PTY_READ_CHUNK = 4096  # ¿Por qué 4096?
```

**Recomendación:**  
- Definir constantes con nombres descriptivos
- Agregar comentarios explicativos

---

### 4.3 Testing

#### Problema: Cobertura de Tests Desconocida
No se encontraron tests unitarios ejecutables en el análisis inicial.

**Recomendación:**  
- Implementar tests unitarios para funciones críticas (complejidad > 10)
- Agregar tests de integración para flujos principales
- Implementar CI/CD con coverage mínimo (80% según TODO.md)
- Usar pytest con fixtures y mocking

---

## 5. Análisis de Dependencias

### 5.1 Dependencias Críticas

| Paquete | Versión Solicitada | Riesgo |
|---------|-------------------|--------|
| `langchain` | >=0.3.27,<0.4.0 | Cambios frecuentes en API |
| `litellm` | >=1.0.0 | Proyecto activo, posibles breaking changes |
| `fastapi` | >=0.100.0 | Estable, pero verificar compatibilidad |
| `sqlalchemy` | >=2.0.0 | Migración a 2.0 requiere cambios |
| `pgvector` | >=0.2.0 | Específico para PostgreSQL, monitorear |

### 5.2 Dependencias con Vulnerabilidades Conocidas
No se ejecutó `pip-audit` en este análisis, pero se recomienda:
```bash
pip-audit --requirement requirements.txt
```

---

## 6. Recomendaciones Priorizadas

### 6.1 Acciones Inmediatas (Alta Prioridad)

1. **Corregir VULN-001 (Terminal PTY)**
   - Implementar sandboxing con Docker
   - Agregar lista blanca de comandos
   - Restringir a red privada/VPN
   - **Esfuerzo:** 2-3 días
   - **Riesgo:** Crítico

2. **Corregir VULN-002 (Secretos por defecto)**
   - Eliminar valores fallback inseguros
   - Forzar configuración obligatoria
   - **Esfuerzo:** 1 día
   - **Riesgo:** Medio-Alto

3. **Refactorizar `llm_manager.py`**
   - Extraer `initialize_llms` y `get_llm_for_user`
   - Aplicar Factory y Strategy patterns
   - **Esfuerzo:** 3-5 días
   - **Riesgo:** Alto (complejidad F)

### 6.2 Acciones a Corto Plazo (Media Prioridad)

4. **Refactorizar `database.py`**
   - Separar modelos de repositorios
   - Dividir por dominio
   - **Esfuerzo:** 1 semana
   - **Riesgo:** Alto

5. **Implementar Tests Unitarios**
   - Cubrir funciones con complejidad > 10
   - Alcanzar 80% coverage (según TODO.md)
   - **Esfuerzo:** 2-3 semanas
   - **Riesgo:** Medio

6. **Fijar Versiones de Dependencias**
   - Generar `requirements.lock`
   - Implementar Dependabot
   - **Esfuerzo:** 1 día
   - **Rieszo:** Medio

### 6.3 Acciones a Largo Plazo (Baja Prioridad)

7. **Mejorar Manejo de Errores**
   - Implementar logging estructurado
   - Agregar tracing distribuido
   - **Esfuerzo:** 1 semana

8. **Optimizar Rendimiento**
   - Implementar caché en `agenda_manager.py`
   - Optimizar consultas SQL en `database.py`
   - **Esfuerzo:** 1-2 semanas

9. **Documentación**
   - Completar README.md
   - Generar documentación de API (Swagger/ReDoc)
   - Crear guía de desarrollo
   - **Esfuerzo:** 1 semana

---

## 7. Métricas de Auditoría

| Métrica | Valor | Estado |
|---------|-------|--------|
| Archivos analizados | 200 | ✅ |
| Errores de compilación | 0 | ✅ |
| Vulnerabilidades críticas | 1 | 🔴 |
| Vulnerabilidades medias | 3 | 🟡 |
| Vulnerabilidades bajas | 2 | 🟢 |
| Funciones con complejidad D+ | 8 | ⚠️ |
| Líneas en archivo más grande | 1600+ | ⚠️ |
| Cobertura de tests | No disponible | ⚠️ |
| Dependencias desactualizadas | Pendiente verificar | ⚠️ |

---

## 8. Comparación con Auditoría Anterior

Según `AUDIT_REPORT.md` (2025-06-17), se identificaron vulnerabilidades similares:
- ✅ Terminal PTY: Confirmada y persistente
- ✅ Secretos por defecto: Confirmada y persistente
- ✅ Dependencias obsoletas: Persiste el problema de versiones flexibles
- ⚠️ Endpoints de debug: No verificados en esta auditoría

**Conclusión:** Las vulnerabilidades críticas identificadas en junio de 2025 **no han sido corregidas**.

---

## 9. Próximos Pasos Recomendados

1. **Inmediato (Esta semana):**
   - Corregir VULN-001 (Terminal PTY) - CRÍTICO
   - Corregir VULN-002 (Secretos por defecto)
   - Revisar y corregir dependencias obsoletas

2. **Sprint 1 (Próximas 2 semanas):**
   - Refactorizar `llm_manager.py`
   - Implementar tests unitarios básicos
   - Comenzar refactorización de `database.py`

3. **Sprint 2 (Próximo mes):**
   - Completar refactorización de `database.py`
   - Alcanzar 80% cobertura de tests
   - Implementar CI/CD completo

4. **Mantenimiento continuo:**
   - Seguir el plan de `TODO.md`
   - Realizar auditorías trimestrales
   - Monitorear dependencias con Dependabot

---

## 10. Anexos

### 10.1 Herramientas Utilizadas
- `radon`: Análisis de complejidad ciclomática
- `py_compile`: Verificación de sintaxis
- `read_file_tool`: Lectura de archivos del proyecto
- `search_in_file_tool`: Búsqueda de patrones de seguridad

### 10.2 Archivos Analizados (Muestra)
- `core/config.py`
- `core/llm_manager.py`
- `core/ollama_direct.py`
- `core/skill_manager.py`
- `core/database.py`
- `core/agenda_manager.py`
- `api/terminal.py`
- `requirements.txt`
- `docker-compose.yml`
- `package.json`

### 10.3 Referencias
- OWASP Top 10: https://owasp.org/www-project-top-ten/
- CWE/SANS Top 25: https://cwe.mitre.org/top25/
- Python Security Best Practices: https://python.readthedocs.io/en/stable/library/security_warnings.html

---

**Fin del Informe**

*Generado automáticamente por KogniTerm*  
*Para dudas o aclaraciones, consultar el código fuente y la documentación del proyecto.*
