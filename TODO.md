# TODO - KognitoAI
**Prioridad:** Alta - Plataforma propia
**Fecha:** 2026-03-18

---

## 🎯 Estado General
Sistema avanzado de exocerebro digital en desarrollo activo. Muchas funcionalidades implementadas (grafos Neo4j, RAG PGVector, agente KAI, bot Telegram, dashboard Next.js). Necesita revisiones de seguridad, optimización y completar tests.

---

## 📌 Fase 1: Revisión de Salud del Sistema

### 1.1 Lectura Obligatoria
- [ ] Leer `docs/Cambios.md` (registro de cambios reciente)
- [ ] Revisar `llm_context.txt` (memoria de sesión reciente del LLM)
- [ ] Revisar `docs/INFORME_CUMPLIMIENTO_KOGNIGESTION.md` (aunque sea otro proyecto, puede haber lecciones)
- [ ] Revisar `docs/refactorization_plan.md` si existe
- [ ] Revisar `docs/resumen_implementacion_esc.md`

### 1.2 Verificación de Deployment
- [ ] ¿Está desplegado en producción? ¿Dónde? (URL, servidor)
- [ ] Revisar logs de errores recientes: `logs/*.log` (buscar ERROR, CRITICAL)
- [ ] Verificar estado de Docker: `docker-compose ps` (todos servicios healthy)
- [ ] Verificar espacio en disco devoluciones (DBs, logs)
- [ ] Probar endpoints básicos (health check, chat, documentos)
- [ ] Verificar uso de CPU/memoria de contenedores

---

## 📌 Fase 2: Seguridad (Plan de Pruebas)

### Documento Guía: `docs/PLAN_PRUEBAS_SEGURIDAD.md`

- [ ] **Análisis Estático (SAST):**
  - [ ] Instalar bandit: `pip install bandit`
  - [ ] Ejecutar: `bandit -r core/ api/`
  - [ ] Revisar y corregir hallazgos

- [ ] **Validación de Entradas:**
  - [ ] Revisar todos los modelos Pydantic en `api/schemas.py` (¿existen?)
  - [ ] Verificar que no haya consultas SQL crudas sin parámetros
  - [ ] Implementar validación de longitud máxima en campos de texto

- [ ] **Revisión de Secrets:**
  - [ ] Verificar que no haya API keys en código (buscar `sk-`, `AIza`, etc.)
  - [ ] Confirmar que todo está en `.env` y `.env` está en `.gitignore`
  - [ ] Revisar que no se expongan secrets en logs

- [ ] **Revisión de Autenticación:**
  - [ ] Verificar que endpoints protegidos requieran token válido
  - [ ] Probar acceso sin token a endpoints sensibles
  - [ ] Revisar expiración de JWT tokens

### Pentesting (opcional pero recomendado)
- [ ] Instalar OWASP ZAP y escanear API en staging
- [ ] Probar SQL injection en parámetros de búsqueda
- [ ] Probar XSS en campos de texto (notas, perfiles)
- [ ] Verificar que no se expongan stack traces en 500 errors

---

## 📌 Fase 3: Tests y Calidad

- [ ] **Tests unitarios:**
  - [ ] Revisar cobertura actual (si hay tests)
  - [ ] Añadir tests para `core/agent.py` (herramientas del agente)
  - [ ] Añadir tests para `core/llm_manager.py`
  - [ ] Tests para herramientas (`tools/`)

- [ ] **Tests de integración:**
  - [ ] Test de flujo completo: crear nota + buscar + recuperar
  - [ ] Test de grafo de conocimiento: crear entidades y relaciones
  - [ ] Test de RAG: upload documento + búsqueda semántica
  - [ ] Test de Telegram bot: comando /start, /chat

- [ ] **CI/CD:**
  - [ ] ¿Hay GitHub Actions o similar?
  - [ ] Configurar pipeline que ejecute tests, lint, bandit
  - [ ] Despliegue automático a staging al hacer push a main

---

## 📌 Fase 4: Optimización (basado en `informe_optimizacion_cpu.md`)

- [ ] Leer `docs/informe_optimizacion_cpu.md`
- [ ] Identificar cuellos de botella de CPU
- [ ] Optimizar queries a Neo4j (¿índices?)
- [ ] Optimizar queries a PostgreSQL/PGVector (¿IVFFlat? ¿HNSW?)
- [ ] Cache de respuestas frecuentes (Redis?)
- [ ] Ajustar `workers` de FastAPI/Gunicorn
- [ ] Considerar async/await en operaciones de DB

---

## 📌 Fase 5: RAG y Grafo de Conocimiento

- [ ] Revisar `docs/rag_implementation_status.md`
- [ ] Verificar que el indexado de código funcione (`kogniterm index .`)
- [ ] Probar búsqueda híbrida (vectorial + grafo)
- [ ] Revisar migración automática de datos existentes
- [x] Eliminar `proactive_knowledge_linker.py` e insights nocturnos (Costo tokens)
- [ ] Ajustar parámetros de embedding (modelo, dimensión)
- [ ] Evaluar calidad de relaciones generadas por Cognee

---

## 📌 Fase 6: Mejoras de UX/UI

- [ ] **Frontend Next.js:**
  - [ ] Revisar `frontend/` errores en consola del navegador
  - [ ] Probar carga de gráficos Neo4j (¿necesita Neo4j Browser?)
  - [ ] Mejorar mensajes de error para el usuario
  - [ ] Añadir indicadores de carga (spinners) en operaciones largas
  - [ ] Responsive: probar en móvil

- [ ] **Telegram Bot:**
  - [ ] Verificar que los botones inline funcionen
  - [ ] Probar envío de imágenes/audio
  - [ ] Revisar que los mensajes largos no se corten
  - [ ] Mejorar `/help` mensaje

---

## 📌 Fase 7: Monitoreo y Mantenimiento

- [ ] **Logs:**
  - [ ] Centralizar logs (¿archivo único o servicio como Loki?)
  - [ ] Añadir rotación de logs (logrotate)
  - [ ] Configurar alertas para errores críticos

- [ ] **Métricas:**
  - [ ] Instalar Prometheus + Grafana (¿o usar simple stats?)
  - [ ] Monitorear: latencia API, uso CPU/memoria, conexiones DB, tamaño de colas
  - [ ] Dashboard interno de métricas

- [ ] **Backups:**
  - [ ] Automatizar backup de PostgreSQL (`pg_dump`)
  - [ ] Automatizar backup de Neo4j (`neo4j-admin dump`)
  - [ ] Backup de archivos subidos (documentos, imágenes)
  - [ ] Probar restauración de backups

---

## 📌 Fase 8: Documentación

- [ ] **README.md actualizado:**
  - [ ] Instrucciones claras de `docker-compose up`
  - [ ] Variables de entorno necesarias (`.env.example`)
  - [ ] Cómo obtener API keys (Google, OpenAI, etc.)
  - [ ] Cómo ejecutar tests
  - [ ] Arquitectura (diagrama actualizado)
  - [ ] Troubleshooting

- [ ] **API Docs:**
  - [ ] ¿Existe OpenAPI/Swagger? Si no, generar con FastAPI
  - [ ] Documentar todos los endpoints: `/chat`, `/documents`, `/notes`, `/agenda`, etc.
  - [ ] Ejemplos de requests/responses

- [ ] **Developer Guide:**
  - [ ] Cómo añadir nueva herramienta al agente
  - [ ] Cómo modificar prompts
  - [ ] Cómo extender modelos de datos
  - [ ] Guía de estilos de código (ya existe?)

---

## 📌 Tareas Específicas Pendientes (Revisar archivos)

- [ ] Revisar `test_*.py` en raíz del proyecto:
  - `test_gliner_precision.py`
  - `test_conceptual_improvements.py`
  - `test_graph_fixes.py`
  - `test_knowledge_gaps_changes.py`
  - `test_database_changes.py`
  - `test_llm_config.py`
  - `test_secret_encryption.py`
  - `test_tavily.py`

  **Acción:** Ejecutar todos los tests y corregir fallos.

- [ ] Revisar `logs.txt` (10MB!) para identificar errores recurrentes
- [ ] Revisar `model_debug.txt` (10MB) para ver problemas con modelos LLM
- [ ] Revisar `verify_*.py` scripts:
  - `verify_changes.py`
  - `verify_graph_system.py`
  - `verify_langgraph_cache.py`
  - `verify_pkg.py`

---

## 🔄 Mantenimiento Continuo

- [ ] **Diario:** Revisar logs de errores (¿hay picos?)
- [ ] **Semanal:** Revisar uso de disco (logs, uploads)
- [ ] **Mensual:** Actualizar dependencias (seguridad)
- [ ] **Trimestral:** Revisar performance y optimizar

---

## 📊 Métricas de Éxito

- [ ] Tiempo de respuesta API < 500ms (p95)
- [ ] Disponibilidad > 99.5%
- [ ] Cobertura de tests > 80%
- [ ] 0 vulnerabilidades críticas en OWASP Top 10
- [ ] Tamaño de logs < 1GB por mes (con rotación)

---

## 📝 Notas

- Usar `kogniterm` para desarrollo (ya que es tu propia herramienta)
- Commitear cambios importantes (pero no subir secrets)
- Taggear releases: `v0.1.0`, `v0.2.0`, etc.

---

**Próxima revisión:** 2026-03-25

**Completadas:**
- [ ]
