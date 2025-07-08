# KognitoAI Database Schema Reference

## Información General
- **Base de datos**: PostgreSQL 15 con extensión pgvector
- **Usuario**: kognito_user
- **Base de datos**: kognito_db
- **Contenedor**: kognito_db

## Arquitectura Principal

### 🔑 Tabla Central: `langchain_pg_embedding`
**La tabla más importante del sistema** - Almacena todos los embeddings vectoriales con columnas optimizadas para búsquedas directas.

```sql
Table "public.langchain_pg_embedding"
      Column      |          Type          | Nullable | Default 
------------------+------------------------+----------+---------
 id               | character varying      | not null | 
 collection_id    | uuid                   |          | 
 embedding        | vector                 |          | 
 document         | character varying      |          | 
 cmetadata        | jsonb                  |          | 
 custom_id        | character varying      |          | 
 uuid             | uuid                   |          | 
 account_id       | uuid                   |          |  ⭐ COLUMNA DIRECTA
 content_type     | character varying(50)  |          |  ⭐ COLUMNA DIRECTA
 workspace_id     | uuid                   |          |  ⭐ COLUMNA DIRECTA
 topic            | character varying(100) |          |  ⭐ COLUMNA DIRECTA
 category         | character varying(50)  |          |  ⭐ COLUMNA DIRECTA
 team_id          | uuid                   |          |  ⭐ COLUMNA DIRECTA
 visibility_teams | jsonb                  |          |  ⭐ COLUMNA DIRECTA
```

**Índices importantes:**
- `idx_langchain_pg_embedding_account_id` (btree)
- `idx_langchain_pg_embedding_team_id` (btree)
- `idx_langchain_pg_embedding_workspace_id` (btree)
- `ix_cmetadata_gin` (gin para búsquedas en JSONB)

**Valores de content_type:**
- `'user_documents'` - Documentos de usuario
- `'user_memories'` - Memorias/recuerdos del usuario

---

## 👤 Gestión de Usuarios

### `accounts`
```sql
        Column        |           Type           | Nullable | Default 
----------------------+--------------------------+----------+---------
 id                   | uuid                     | not null | 
 name                 | character varying(255)   |          | 
 email                | character varying(255)   |          | 
 hashed_password      | character varying(255)   |          | 
 username             | character varying(255)   |          | 
 timezone             | character varying(255)   |          | 
 custom_system_prompt | text                     |          | 
 created_at           | timestamp with time zone |          | now()
 is_admin             | boolean                  | not null | false
 is_active            | boolean                  |          | 
```

### `platform_identities`
Vincula cuentas con identidades de plataformas externas (Telegram, etc.)

### `verification_codes`
Códigos de verificación para autenticación.

---

## 👥 Sistema de Equipos

### `teams`
```sql
   Column   |           Type           | Nullable | Default 
------------+--------------------------+----------+---------
 id         | uuid                     | not null | 
 name       | character varying(255)   | not null | 
 created_at | timestamp with time zone |          | now()
 admin_id   | uuid                     | not null | 
```

### `team_members`
Tabla de relación muchos-a-muchos entre usuarios y equipos.

---

## 🏢 Sistema de Workspaces

### `workspaces`
```sql
    Column     |           Type           | Nullable | Default 
---------------+--------------------------+----------+---------
 id            | uuid                     | not null | 
 account_id    | uuid                     | not null | 
 name          | character varying(255)   | not null | 
 system_prompt | text                     |          | 
 created_at    | timestamp with time zone |          | now()
```

### `workspace_collections`
Colecciones específicas de workspaces.

### `workspace_collection_documents`
Documentos dentro de colecciones de workspaces.

### `workspace_document_chunks`
Chunks de documentos en workspaces.

---

## 📚 Gestión de Documentos y Colecciones

### `user_document_topics`
**Tabla clave para colecciones de documentos**
```sql
    Column    |           Type           | Nullable | Default 
--------------+--------------------------+----------+---------
 id           | uuid                     | not null | 
 account_id   | uuid                     | not null | 
 workspace_id | uuid                     |          | 
 team_id      | uuid                     |          | 
 name         | character varying(255)   | not null | 
 description  | text                     |          | 
 created_at   | timestamp with time zone |          | now()
 updated_at   | timestamp with time zone |          | 
 is_global    | boolean                  |          | false
```

**Índices únicos importantes:**
- `ix_account_personal_topic` - Colecciones personales únicas por usuario
- `ix_account_team_topic` - Colecciones de equipo únicas
- `ix_account_workspace_topic` - Colecciones de workspace únicas

### `langchain_pg_collection`
```sql
  Column   |       Type        | Nullable | Default 
-----------+-------------------+----------+---------
 uuid      | uuid              | not null | 
 name      | character varying | not null | 
 cmetadata | json              |          | 
```

### `github_documents`
Documentos importados desde repositorios de GitHub.

---

## 📝 Contenido del Usuario

### `notas`
```sql
   Column   |           Type           | Nullable |              Default              
------------+--------------------------+----------+-----------------------------------
 id         | integer                  | not null | nextval('notas_id_seq'::regclass)
 account_id | uuid                     | not null | 
 title      | character varying        |          | 
 content    | text                     | not null | 
 category   | character varying        |          | 
 created_at | timestamp with time zone |          | 
 updated_at | timestamp with time zone |          | 
 embedding  | vector(384)              |          | 
 team_id    | uuid                     |          | 
```

### `memories`
Memorias/recuerdos del usuario con embeddings vectoriales.

### `recordatorios`
Sistema de recordatorios y notificaciones.

---

## 📅 Agenda y Eventos

### `agenda_events`
```sql
       Column       |           Type           | Nullable |                  Default                  
--------------------+--------------------------+----------+-------------------------------------------
 id                 | integer                  | not null | nextval('agenda_events_id_seq'::regclass)
 account_id         | uuid                     | not null | 
 description        | character varying        | not null | 
 event_datetime_utc | timestamp with time zone | not null | 
 is_active          | boolean                  | not null | 
 job_name           | character varying        |          | 
 team_id            | uuid                     |          | 
```

---

## 🔍 Sistema de Análisis

### `analysis_tasks`
```sql
     Column     |           Type           | Nullable | Default 
----------------+--------------------------+----------+---------
 id             | uuid                     | not null | 
 account_id     | uuid                     | not null | 
 file_name      | character varying        | not null | 
 status         | character varying        | not null | 
 result_payload | jsonb                    |          | 
 error_message  | text                     |          | 
 created_at     | timestamp with time zone |          | now()
 updated_at     | timestamp with time zone |          | 
 analysis_type  | character varying(50)    |          | 
```

### `mindmap_tasks`
Tareas específicas para generación de mapas mentales.

### `proactive_insights`
Insights proactivos generados por el sistema.

### `process_status`
Estado de procesos en ejecución.

---

## 💬 Sistema de Chat

### `chat_threads`
Hilos de conversación del usuario.

### `langchain_chat_history`
Historial de conversaciones usando LangChain.

---

## 🔧 Tablas de Soporte

### `profiles`
Perfiles adicionales de usuario.

---

## 🚨 Reglas Importantes para Desarrollo

### ✅ Búsquedas Optimizadas
**USAR SIEMPRE las columnas directas en lugar de buscar en cmetadata:**

```sql
-- ✅ CORRECTO - Búsqueda optimizada
SELECT * FROM langchain_pg_embedding 
WHERE account_id = 'uuid-here' 
  AND content_type = 'user_documents'
  AND team_id = 'team-uuid';

-- ❌ INCORRECTO - Búsqueda lenta
SELECT * FROM langchain_pg_embedding 
WHERE cmetadata->>'account_id' = 'uuid-here';
```

### ✅ Compartir Documentos con Equipos
```sql
-- Actualizar solo la columna team_id directa
UPDATE langchain_pg_embedding 
SET team_id = 'team-uuid'
WHERE account_id = 'user-uuid' 
  AND content_type = 'user_documents'
  AND cmetadata->>'file_name' = 'documento.pdf';
```

### ✅ Filtros por Workspace
```sql
-- Documentos de un workspace específico
SELECT * FROM langchain_pg_embedding 
WHERE account_id = 'user-uuid'
  AND workspace_id = 'workspace-uuid'
  AND content_type = 'user_documents';
```

### ✅ Colecciones (Topics)
```sql
-- Documentos de una colección específica
SELECT * FROM langchain_pg_embedding 
WHERE account_id = 'user-uuid'
  AND topic = 'nombre-coleccion'
  AND content_type = 'user_documents';
```

---

## 📊 Tipos de Contenido

| content_type | Descripción | Uso |
|--------------|-------------|-----|
| `user_documents` | Documentos subidos por el usuario | RAG, análisis de documentos |
| `user_memories` | Memorias/recuerdos del usuario | Sistema de memoria contextual |

---

## 🔗 Relaciones Clave

- `accounts` → Tabla central, referenciada por casi todas las demás
- `langchain_pg_embedding` → Tabla de embeddings con columnas optimizadas
- `user_document_topics` → Define colecciones de documentos
- `teams` → Sistema de colaboración
- `workspaces` → Aislamiento de contextos de trabajo

---

## 📋 Ejemplos de Consultas Comunes

### Obtener documentos de un usuario
```sql
SELECT DISTINCT cmetadata->>'file_name' as file_name,
       cmetadata->>'title' as title,
       topic,
       team_id IS NOT NULL as is_shared
FROM langchain_pg_embedding
WHERE account_id = 'user-uuid'
  AND content_type = 'user_documents'
  AND cmetadata->>'type' = 'document_chunk';
```

### Listar colecciones de un usuario
```sql
SELECT name, description, created_at,
       workspace_id IS NOT NULL as is_workspace_collection,
       team_id IS NOT NULL as is_team_collection
FROM user_document_topics
WHERE account_id = 'user-uuid'
ORDER BY created_at DESC;
```

### Documentos compartidos con un equipo
```sql
SELECT DISTINCT cmetadata->>'file_name' as file_name,
       cmetadata->>'title' as title,
       topic
FROM langchain_pg_embedding
WHERE team_id = 'team-uuid'
  AND content_type = 'user_documents'
  AND cmetadata->>'type' = 'document_chunk';
```

### Buscar en memorias de usuario
```sql
SELECT cmetadata->>'content' as content,
       cmetadata->>'type' as memory_type,
       category
FROM langchain_pg_embedding
WHERE account_id = 'user-uuid'
  AND content_type = 'user_memories'
  AND cmetadata->>'content' ILIKE '%término de búsqueda%';
```

---

## ⚠️ Consideraciones de Migración

### Estructura Antigua vs Nueva
- **❌ ANTES (OBSOLETO)**: Búsquedas por `collection_id` en `langchain_pg_collection`
- **✅ AHORA (OBLIGATORIO)**: Búsquedas directas por `account_id`, `content_type`, `team_id`, etc.

**⚠️ IMPORTANTE**: Ya NO usar `collection_id` en nuevas consultas. Todas las herramientas y funciones deben usar las columnas directas.

### Migración de Consultas Obsoletas

#### ❌ CONSULTA OBSOLETA (NO USAR):
```sql
-- OBSOLETO - Buscar por collection_id
SELECT * FROM langchain_pg_embedding
WHERE collection_id = 'uuid-here'
  AND cmetadata->>'type' = 'document_chunk';
```

#### ✅ CONSULTA ACTUALIZADA (USAR):
```sql
-- CORRECTO - Buscar por account_id y content_type
SELECT * FROM langchain_pg_embedding
WHERE account_id = 'user-uuid'
  AND content_type = 'user_documents'
  AND cmetadata->>'type' = 'document_chunk';
```

### Metadatos en cmetadata vs Columnas Directas
- **cmetadata**: Información específica del documento (file_name, title, type)
- **Columnas directas**: Información de organización y permisos (account_id, team_id, workspace_id, topic)

---

## 🔍 Debugging y Troubleshooting

### Verificar estructura de cmetadata
```sql
SELECT DISTINCT jsonb_object_keys(cmetadata) as metadata_keys
FROM langchain_pg_embedding
WHERE account_id = 'user-uuid'
LIMIT 10;
```

### Contar documentos por tipo
```sql
SELECT content_type,
       cmetadata->>'type' as chunk_type,
       COUNT(*) as count
FROM langchain_pg_embedding
WHERE account_id = 'user-uuid'
GROUP BY content_type, cmetadata->>'type';
```

### Verificar índices activos
```sql
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'langchain_pg_embedding';
```

---

**Fecha de actualización**: 2025-07-07
**Versión de PostgreSQL**: 15.12
**Extensiones**: pgvector para embeddings vectoriales
**Contenedor**: kognito_db (docker)
**Credenciales**: Ver archivo .env
