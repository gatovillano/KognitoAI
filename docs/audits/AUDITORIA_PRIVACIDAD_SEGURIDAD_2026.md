**Auditoría de Privacidad y Seguridad de Datos - KognitoAI**  
**Resumen Ejecutivo**  
Se realizó una auditoría integral de privacidad y seguridad de datos en el proyecto KognitoAI. Se identificaron **vulnerabilidades críticas, medias y bajas**, junto con un plan de mitigación priorizado y recomendaciones de mejora continua.  
**Fecha de auditoría:** 2026-08-13  
   
 **Alcance:** Arquitectura, almacenamiento de PII, autenticación/autorización, cifrado, endpoints API, logs, backups y cumplimiento normativo.  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANUlEQVR4nO3OMQ2AABAAsSPBCUZfEnoYmFDBhAU2QtIq6DIzW7UHAMBfnGt1V8fXEwAAXrse/wcF74lXkIsAAAAASUVORK5CYII=)  
**1. Arquitectura y Flujos de Datos Sensibles**  
**Hallazgos**  
- **Estructura del proyecto:** Directorio principal /home/gato/Proyectos/KognitoAI/kognito-ai con carpetas src, api, core, storage, skills, tests, scripts, telegram_gateway.  
- **Componentes sensibles identificados:**  
  - Modelos de Account que almacenan PII (email, teléfono, biografía, prompts personalizados, instrucciones de heartbeat).  
  - Sistema de autenticación con JWT y refresh tokens.  
  - Soporte para MFA.  
  - Integración con Telegram (telegram_gateway).  
  - Endpoints de API y modo debug.  
  - Sistema de logs.  
  - Sistema de exports y backups.  
- **Datos en tránsito:** Se detectaron referencias a Authorization: Bearer <api_key> en core/ollama_direct.py, lo que indica uso de tokens en cabeceras HTTP.  
- **Datos en reposo:** No se encontró evidencia de cifrado automático de campos PII en la base de datos. Existe una migración d6b59d7b748c_enable_pgcrypto_extension.py que sugiere que se habilitó pgcrypto, pero no se confirmó su aplicación efectiva en columnas sensibles.  
**Riesgo**  
**Alto** - Exposición de PII en texto plano en base de datos y potencial fuga de tokens en logs o respuestas API.  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANUlEQVR4nO3OMQ2AABAAsSNhZscaUpheJwqQgQU2QtIq6DIze3UGAMBf3Gu1VcfXEwAAXrseopcEQ2uoYnwAAAAASUVORK5CYII=)  
**2. Almacenamiento y Procesamiento de Datos Personales (PII)**  
**Hallazgos**  
- **Campos PII detectados:**  
  - Email (posiblemente usado como identificador único).  
  - Teléfono.  
  - Biografía.  
  - Prompts personalizados del usuario.  
  - Instrucciones de heartbeat.  
- **Modelos y migraciones:**  
  - 0eca9c52eb37_add_new_fields_to_account_model.py - Agrega campos nuevos al modelo Account.  
  - bb9b21bbc3c9_add_mfa_fields_to_account.py - Agrega campos MFA.  
  - 2f8c0071b1af_create_user_secrets_table.py - Crea tabla user_secrets para almacenar secretos.  
- **Falta de cifrado:** No se encontró evidencia de cifrado de campos sensibles antes de persistencia. La tabla user_secrets podría ser un mecanismo parcial, pero su implementación no está clara.  
**Cumplimiento Normativo**  
- **GDPR / CCPA / LOPD:** Riesgo de incumplimiento por almacenamiento de PII sin cifrado y sin mecanismos claros de retención/purga.  
**Riesgo**  
**Crítico** - PII almacenada en texto plano sin cifrado.  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANUlEQVR4nO3OQQmAABRAsSd40A5GMORPYEt7WMGbCFuCLTNzVFcAAPzFvVZbdX49AQDgtf0BSrIDUgOg4eAAAAAASUVORK5CYII=)  
**3. Mecanismos de Autenticación, Autorización y Cifrado**  
**Hallazgos**  
- **Autenticación:**  
  - JWT (api/auth.py).  
  - Refresh tokens.  
  - MFA disponible (bb9b21bbc3c9_add_mfa_fields_to_account.py).  
- **Autorización:** No se analizaron en detalle los controles de autorización por rol en todos los endpoints.  
- **Cifrado:**  
  - Referencias a pgcrypto en migraciones (d6b59d7b748c_enable_pgcrypto_extension.py).  
  - Uso de hashlib.md5 en core/agents/deep_researcher_utils.py para generación de IDs (no criptográficamente seguro para otros usos).  
  - No se encontró evidencia de cifrado de datos en reposo a nivel de aplicación (AES/RSA).  
  - No se confirmó uso de TLS/SSL obligatorio en todas las comunicaciones.  
- **Gestión de secretos:**  
  - Archivo .env presente en el repositorio con permisos 600 (buena práctica).  
  - Variables de entorno para API keys (TAVILY_API_KEY, api_key en ollama_direct.py).  
**Riesgo**  
**Alto** - Falta de cifrado de datos sensibles en reposo y posible uso de algoritmos no seguros (MD5).  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANElEQVR4nO3OQQmAABRAsSdYxKa/i8WMIR7ECt5E2BJsmZmt2gMA4C+Otbqr8+sJAACvXQ85PAYartXEogAAAABJRU5ErkJggg==)  
**4. Auditoría de Endpoints API y Exposición de Datos**  
**Hallazgos**  
- **Endpoints detectados:**  
  - api/auth.py - Autenticación.  
  - api/admin_llm.py, api/admin_pipeline.py - Administración.  
  - api/chat.py, api/chat_share.py - Chat y compartición.  
  - api/analysis.py, api/analysis_share.py - Análisis y compartición.  
  - api/deep_research.py - Investigación profunda.  
  - api/agenda.py, api/caldav.py, api/caldav_router.py - Agenda/CalDAV.  
  - api/documents.py, api/collections.py, api/contact_profiles.py - Documentos y perfiles.  
- **Modo debug:** No se confirmó si existen endpoints de debug accesibles en producción sin restricciones.  
- **Exposición de PII:** Riesgo de que endpoints retornen más datos de los necesarios (falta de revisión de schemas de respuesta).  
**Riesgo**  
**Medio** - Posible sobre-exposición de datos en respuestas API y falta de rate limiting/throttling visible en el codebase analizado.  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANklEQVR4nO3OQQmAABRAsScYxpg/h5VMYARvRrCCNxG2BFtmZquOAAD4i3Ot7mr/egIAwGvXA224BcUMk6pDAAAAAElFTkSuQmCC)  
**5. Integraciones con Terceros y Servicios Externos**  
**Hallazgos**  
- **Telegram:** Integración mediante telegram_gateway. Requiere revisión de qué datos se envían a la API de Telegram y su retención.  
- **Tavily:** Uso de tavily_api_key para búsquedas web (core/agents/deep_researcher_utils.py).  
- **Ollama:** Conexión a modelos locales/remotos con api_key opcional.  
- **LLMs externos:** Referencias a múltiples proveedores en migraciones (20250124_missing_providers.py).  
**Riesgo**  
**Medio** - Transferencia de PII a servicios terceros sin confirmación de acuerdos de procesamiento (DPA) o cifrado extremo a extremo.  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANUlEQVR4nO3OMQ2AABAAsSNBCUrfD6LYGNDAgAU2QtIq6DIzW7UHAMBfHGt1V+fXEwAAXrseHDAF/orRG+cAAAAASUVORK5CYII=)  
**6. Logs, Backups y Exports**  
**Hallazgos**  
- **Logs:** No se encontró evidencia de sanitización de PII en logs. Existe riesgo de que emails, tokens o contenido de prompts se registren en texto plano.  
- **Backups/Exports:** No se detectó mecanismo de anonimización antes de backups o exports.  
- **Retención:** No se encontró política de retención automática para tokens expirados, códigos de verificación o datos antiguos.  
**Riesgo**  
**Alto** - PII en logs y backups sin protección ni retención definida.  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANElEQVR4nO3OUQmAABBAsSeIWMICprwEpjSIFfwTYUuwZWaO6goAgL+412qrzq8nAAC8tj8tdQNNdXaCdAAAAABJRU5ErkJggg==)  
**7. Vulnerabilidades Detectadas**  
**Críticas**  
1. **PII en texto plano en base de datos** - Campos sensibles sin cifrado.  
2. **Falta de jobs de retención/purga** - Tokens y códigos expirados persisten indefinidamente.  
3. **Posible exposición de endpoints de debug en producción** - Sin confirmar restricciones.  
**Medias**  
1. **Falta de cifrado de datos en reposo a nivel aplicación** - Dependencia solo en cifrado de transporte.  
2. **Uso de MD5 para generación de IDs** - No es criptográficamente seguro.  
3. **Posible sobre-exposición en respuestas API** - Sin revisión de schemas.  
**Bajas**  
1. **Gestión de secretos en variables de entorno** - Aceptable pero mejorable con vault.  
2. **Falta de rate limiting visible** - Potencial abuso de endpoints.  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANklEQVR4nO3OUQmAABBAsSeYxZyXSzCJASxgACv4J8KWYMvMbNURAAB/ca7VXe1fTwAAeO16AKe+BdmJqrPdAAAAAElFTkSuQmCC)  
**8. Plan de Mitigación Priorizado**  
**Prioridad Alta (Críticas)**  
| | | | |  
|-|-|-|-|  
| **#** | **Acción** | **Responsable** | **Plazo** |   
| 1 | Cifrar campos PII en base de datos usando pgcrypto o cifrado a nivel aplicación (AES-256). | Backend | 2 semanas |   
| 2 | Implementar jobs automáticos de retención y purga de tokens, refresh tokens y códigos de verificación expirados (ej. Celery Beat o APScheduler). | Backend | 1 semana |   
| 3 | Bloquear endpoints de debug en producción (middleware de entorno o feature flags). | Backend/DevOps | 3 días |   
   
**Prioridad Media (Medias)**  
| | | | |  
|-|-|-|-|  
| **#** | **Acción** | **Responsable** | **Plazo** |   
| 4 | Implementar cifrado de datos sensibles antes de enviarlos a servicios terceros (Telegram, Tavily). | Backend | 2 semanas |   
| 5 | Reemplazar uso de MD5 por SHA-256 o UUIDs para generación de IDs estables. | Backend | 1 semana |   
| 6 | Realizar auditoría de schemas de respuesta API para eliminar sobre-exposición de PII. | Backend | 1 semana |   
| 7 | Implementar rate limiting y throttling en endpoints sensibles. | Backend | 1 semana |   
   
**Prioridad Baja (Mejora Continua)**  
| | | | |  
|-|-|-|-|  
| **#** | **Acción** | **Responsable** | **Plazo** |   
| 8 | Implementar vault de secretos (HashiCorp Vault, AWS Secrets Manager, etc.) en lugar de .env. | DevOps | 1 mes |   
| 9 | Agregar monitoreo y alertas de seguridad (intentos de acceso no autorizados, patrones anómalos). | DevOps/Seguridad | 1 mes |   
| 10 | Documentar DPA con proveedores terceros (Telegram, Tavily, Ollama) y garantizar cifrado en tránsito. | Legal/Tech | 1 mes |   
   
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANUlEQVR4nO3OQQmAABRAsSd49m4tA8nPaQJjWMGbCFuCLTOzV2cAAPzFvVZbdXw9AQDgtesBorcEPwOKyvQAAAAASUVORK5CYII=)  
**9. Recomendaciones Adicionales**  
1. **Cumplimiento normativo:** Realizar una evaluación formal de GDPR/LOPD/CCPA con un especialista legal.  
2. **Privacidad desde el diseño:** Incluir revisión de privacidad en el ciclo de desarrollo (Privacy by Design).  
3. **Auditoría continua:** Programar auditorías trimestrales de seguridad y privacidad.  
4. **Capacitación:** Entrenar al equipo en manejo seguro de PII y secretos.  
5. **Red teaming:** Realizar pruebas de penetración periódicas.  
6. **Política de retención:** Definir y automatizar políticas de retención de datos según normativa aplicable.  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANUlEQVR4nO3OMQ2AABAAsSPBCj7fFwtCmJHAjAU2QtIq6DIzW7UHAMBfnGt1V8fHEQAA3rsexOkF3va0dq8AAAAASUVORK5CYII=)  
**10. Próximos Pasos**  
1. Aprobar el plan de mitigación priorizado.  
2. Asignar responsables y plazos para cada acción.  
3. Ejecutar las acciones de Prioridad Alta en las próximas 2 semanas.  
4. Revisar el progreso en 30 días y ajustar el plan según hallazgos.  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANUlEQVR4nO3OMQ2AABAAsSNBCUpfD6ZYGZDAgAU2QtIq6DIzW7UHAMBfHGt1V+fXEwAAXrseHCoGAe/SKtAAAAAASUVORK5CYII=)  
**Fin del Informe de Auditoría**  
