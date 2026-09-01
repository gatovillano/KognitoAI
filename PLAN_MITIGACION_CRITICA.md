# Plan de Mitigación — Hallazgos Críticos de Auditoría de Privacidad y Seguridad

**Fecha:** 2026-08-13
**Alcance:** 3 hallazgos críticos identificados en la auditoría de privacidad y seguridad de datos de KognitoAI.
**Responsable de ejecución:** Equipo Backend (con apoyo de DevOps y Legal).

---

## Hallazgo Crítico 1: PII almacenada en texto plano en la base de datos

### Evidencia verificada
- `core/database.py` l.165-183: Las columnas `accounts.phone`, `accounts.bio`, `accounts.custom_system_prompt` y `accounts.custom_heartbeat_instructions` son de tipo `String`/`Text` sin cifrado.
- `alembic/versions/d6b59d7b748c_enable_pgcrypto_extension.py`: Solo ejecuta `CREATE EXTENSION IF NOT EXISTS pgcrypto`. No aplica `pgp_sym_encrypt` a ninguna columna existente.
- `core/database.py` l.1260-1287 (`UserSecret`): La tabla `user_secrets` sí usa `encrypted_value` (pgcrypto), pero exclusivamente para API keys del usuario, no para PII.

### Campos PII afectados
| Tabla | Columna | Tipo de dato | Riesgo |
|-------|---------|-------------|--------|
| `accounts` | `email` | String(255) | Identificador único — actúa como índice de búsqueda |
| `accounts` | `phone` | String(255) | Datos sensibles de contacto |
| `accounts` | `bio` | Text | Información personal del usuario |
| `accounts` | `custom_system_prompt` | Text | Contenido privado del usuario |
| `accounts` | `custom_heartbeat_instructions` | Text | Instrucciones privadas del usuario |
| `contact_profiles` | `email`, `phone` | String(255) | PII de contactos externos |
| `emails` | `from_address`, `to_addresses`, `body_text`, `body_html` | Text | Contenido de correos electrónicos |
| `agenda_events` | `summary`, `description`, `location` | Text | Datos personales de eventos |
| `notas` | `title`, `content`, `visual_content` | Text | Contenido privado del usuario |

### Acción de mitigación
**Opción A (recomendada — pgcrypto a nivel de columna):**
1. Crear una migración Alembic que altere cada columna PII para usar `TEXT` + una columna de "ciphertext" paralela, o bien aplicar `pgp_sym_encrypt` directamente.
2. Implementar un servicio de cifrado/descifrado (`core/services/encryption.py`) que:
   - Use `pgp_sym_encrypt` con una clave maestra almacenada en variables de entorno (`ENCRYPTION_KEY`) o en un vault.
   - Exponga `encrypt_field(value: str) -> str` y `decrypt_field(ciphertext: str) -> str`.
3. Modificar todos los repositories y endpoints que lean/esciban estas columnas para usar el servicio de cifrado.
4. Ejecutar un script de backfill (`scripts/backfill_encrypt_pii.py`) que cifre los datos existentes en texto plano.

**Opción B (cifrado a nivel de aplicación — más portátil):**
1. Usar `cryptography.fernet` o `cryptography.AESGCM` con claves por cuenta (derivadas de una clave maestra + `account_id`).
2. Cifrar en el modelo ORM mediante `@property` o `hybrid_property` que transparente el cifrado al resto de la aplicación.
3. Backfill de datos existentes.

**Plazo:** 2 semanas
**Responsable:** Backend lead

---

## Hallazgo Crítico 2: Ausencia de jobs de retención/purga automática

### Evidencia verificada
- `core/database.py` l.948-958 (`VerificationCode`): Tiene `expires_at` pero no hay ningún job programado que elimine códigos expirados.
- `core/database.py` l.1291-1308 (`SharedAnalysisLink`) y l.1312-1331 (`SharedConversationLink`): Tienen `expiry_date` pero sin purga automática.
- Los tokens JWT no se almacenan en BD (se validan por `exp`), pero si se implementan refresh tokens persistentes, necesitarían purga.
- No se encontró ningún archivo que contenga `celery beat`, `apscheduler`, o `BackgroundTasks` para limpieza programada.

### Datos afectados que necesitan purga
| Tabla | Campo de expiración | Retención recomendada |
|-------|---------------------|----------------------|
| `verification_codes` | `expires_at` | 24h después de la expiración |
| `shared_analysis_links` | `expiry_date` | 7 días después de la expiración |
| `shared_conversation_links` | `expiry_date` | 7 días después de la expiración |
| `shared_album_links` | `expiry_date` | 7 días después de la expiración |
| `onlyoffice_document_shares` | (sin fecha) | Revisar si necesitan expiración |
| `episodic_memory` | `occurred_at` | Retención de 12 meses (GDPR) |
| `analytics_events` | `timestamp` | Retención de 6 meses |

### Acción de mitigación
1. Crear un módulo `core/services/data_retention.py` con una función `run_purge_jobs()` que:
   - Elimine `verification_codes` con `expires_at < NOW() - INTERVAL '24 hours'`.
   - Elimine `shared_*_links` con `expiry_date < NOW() - INTERVAL '7 days'`.
   - Archive (antes de eliminar) los registros purgados en una tabla `purged_records` para auditoría.
2. Programar el job mediante:
   - **Celery Beat** (si ya se usa Celery en el proyecto), o
   - **APScheduler** integrado en el proceso principal, o
   - Un cron job externo que ejecute `python -m scripts.run_purge`.
3. Ejecutar una purga inicial manual para limpiar datos existentes.
4. Documentar la política de retención en `docs/retention_policy.md`.

**Plazo:** 1 semana
**Responsable:** Backend lead

---

## Hallazgo Crítico 3: Posible exposición de endpoints de debug en producción

### Evidencia verificada
- `api/auth.py` l.412-426: La función `_verify_debug_access` verifica `settings.debug_mode` y una lista blanca de IPs (`DEBUG_ALLOWED_IPS`).
- Endpoints que usan `_verify_debug_access`:
  - `GET /auth/debug-token` (l.428)
  - `POST /auth/emergency-token` (l.450)
  - `GET /auth/clear-tokens` (l.471)
- Estos endpoints están protegidos por la dependencia, pero la protección depende de que `debug_mode` esté desactivado en producción. Si por error se activa, quedarían expuestos.

### Acción de mitigación
1. **Verificación inmediata:** Confirmar que `settings.debug_mode` es `False` en todas las configuraciones de producción (`.env.production`, variables de entorno del contenedor).
2. **Hardening de `_verify_debug_access`:**
   - Añadir una verificación adicional de variable de entorno `DEBUG_ENDPOINTS_DISABLED=true` que bloquee incluso si `debug_mode` está activo.
   - Requerir autenticación de administrador (además de la IP blanca) para los endpoints de debug.
   - Retirar el endpoint `POST /auth/emergency-token` que puede generar tokens para cualquier cuenta de Telegram si se activa el modo debug.
3. **Auditoría de otros endpoints sensibles:** Revisar `api/admin_llm.py`, `api/admin_pipeline.py`, `api/logs.py` para confirmar que están protegidos por `get_current_admin_account`.
4. **Feature flag:** Usar un feature flag (ej. `ENABLE_DEBUG_ENDPOINTS`) en lugar de depender de `debug_mode` para controlar la exposición.

**Plazo:** 3 días
**Responsable:** Backend + DevOps

---

## Plan de ejecución resumido

| # | Acción | Prioridad | Plazo | Responsable | Dependencias |
|---|--------|-----------|-------|-------------|--------------|
| 1 | Cifrar campos PII en BD (pgcrypto o AES-256) | Crítica | 2 semanas | Backend | Ninguna |
| 2 | Implementar jobs de retención/purga automática | Crítica | 1 semana | Backend | Ninguna |
| 3 | Bloquear/ hardening endpoints de debug en producción | Crítica | 3 días | Backend/DevOps | Ninguna |
| 4 | Revisar y hardening endpoints admin (admin_llm, admin_pipeline, logs) | Media | 1 semana | Backend | #3 |
| 5 | Reemplazar MD5 por SHA-256/UUID en deep_researcher_utils.py | Media | 1 semana | Backend | Ninguna |
| 6 | Auditoría de schemas de respuesta API (sobre-exposición PII) | Media | 1 semana | Backend | #1 |
| 7 | Implementar rate limiting/throttling en endpoints sensibles | Media | 1 semana | Backend | Ninguna |
| 8 | Configurar vault de secretos (en lugar de .env) | Baja | 1 mes | DevOps | #1 |
| 9 | Monitoreo y alertas de seguridad | Baja | 1 mes | DevOps/Seguridad | #2, #3 |
| 10 | Documentar DPA con proveedores terceros | Baja | 1 mes | Legal/Tech | Ninguna |

---

## Criterios de aceptación

- [ ] Todos los campos PII identificados están cifrados en reposo (verificar con una query SQL directa que muestre texto plano).
- [ ] Job de purga ejecutado al menos una vez y programado para ejecución diaria.
- [ ] Endpoints de debug devuelven 404 cuando `debug_mode` es `False` o `DEBUG_ENDPOINTS_DISABLED=true`.
- [ ] MD5 reemplazado en todos los usos de `core/agents/deep_researcher_utils.py`.
- [ ] Rate limiting activo en endpoints de autenticación y administrativos.

---

## Notas

- Este plan se deriva de la auditoría de privacidad y seguridad de datos del 2026-08-13.
- Se recomienda una revisión de progreso en 30 días y auditorías trimestrales subsiguientes.
- Los datos existentes en texto plano deben ser migrados (backfill) como parte de la acción #1, no solo nuevos datos.