# Documentación de Funcionamiento de Workspaces

## 🎯 Introducción

Los **Workspaces** (espacios de trabajo) son una funcionalidad central del sistema que permite a los usuarios organizar y separar sus proyectos, tareas y contenido en espacios independientes. Cada workspace actúa como un contenedor aislado que agrupa elementos relacionados y permite la colaboración entre usuarios mediante un sistema de permisos granular.

## 🏗️ Arquitectura de Datos

### Modelo Principal: Workspace

```python
class Workspace(Base):
    id: UUID (primary_key)
    account_id: UUID (foreign_key -> Account)
    name: String(255) - obligatorio
    system_prompt: Text - opcional (prompt específico para IA)
    color: String(7) - opcional (color hex para identificación visual)
    created_at: DateTime
```

**Características:**
- **Identificador único**: Utiliza UUID para garantizar unicidad global
- **Propiedad**: Cada workspace pertenece a una cuenta creadora
- **Personalización**: Permite prompts de sistema específicos y colores personalizados
- **Timestamps**: Registro automático de creación

### Sistema de Permisos: WorkspacePermission

```python
class WorkspacePermission(Base):
    id: UUID (primary_key)
    workspace_id: UUID (foreign_key -> Workspace)
    account_id: UUID (foreign_key -> Account)
    role: String(50) - obligatorio
    created_at: DateTime
    updated_at: DateTime
```

**Roles Disponibles:**

| Rol | Permisos | Descripción |
|-----|----------|-------------|
| `owner` | **Completo** | Propietario con control total del workspace |
| `editor` | **Modificación** | Puede editar y gestionar contenido, compartir con otros |
| `viewer` | **Solo lectura** | Acceso de visualización sin permisos de modificación |

## 🔗 Integración con Otros Componentes

Los workspaces se integran con múltiples entidades del sistema:

### 1. **Tareas (Tasks)**
```python
class Task(Base):
    account_id: UUID
    workspace_id: UUID (opcional)
    # Las tareas pueden pertenecer a un workspace específico
```

### 2. **Notas (Notes)**
```python
class Nota(Base):
    account_id: UUID
    workspace_id: UUID (opcional)
    # Las notas pueden organizarse por workspace
```

### 3. **Eventos de Agenda (AgendaEvent)**
```python
class AgendaEvent(Base):
    account_id: UUID
    workspace_id: UUID (opcional)
    # Los eventos pueden asociarse a workspaces
```

### 4. **Hilos de Chat (ChatThread)**
```python
class ChatThread(Base):
    account_id: UUID
    workspace_id: UUID (opcional)
    # Los chats pueden organizarse por proyecto/workspace
```

### 5. **Temas de Documentos (UserDocumentTopic)**
```python
class UserDocumentTopic(Base):
    account_id: UUID
    workspace_id: UUID (opcional)
    # Las colecciones de documentos pueden ser específicas del workspace
```

## 🌐 API Endpoints

### Gestión Básica de Workspaces

#### 1. **Listar Workspaces**
```http
GET /api/workspaces
```
**Parámetros:**
- `skip` (int): Elementos a omitir (paginación)
- `limit` (int): Máximo de elementos a devolver (1-100)

**Respuesta:**
```json
{
    "total": 5,
    "workspaces": [
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "name": "Proyecto Alpha",
            "system_prompt": "Actúa como asistente del proyecto Alpha...",
            "color": "#007bff",
            "created_at": "2025-12-22T10:00:00Z"
        }
    ]
}
```

#### 2. **Crear Workspace**
```http
POST /api/workspaces
```
**Body:**
```json
{
    "name": "Nuevo Proyecto",
    "system_prompt": "Prompt específico para este workspace",
    "color": "#28a745"
}
```

#### 3. **Obtener Detalles de Workspace**
```http
GET /api/workspaces/{workspace_id}
```

#### 4. **Actualizar Workspace**
```http
PUT /api/workspaces/{workspace_id}
```
**Body:**
```json
{
    "name": "Nombre Actualizado",
    "system_prompt": "Nuevo prompt del sistema",
    "color": "#dc3545"
}
```

#### 5. **Eliminar Workspace**
```http
DELETE /api/workspaces/{workspace_id}
```
**Restricciones:** Solo puede eliminarlo el `owner` del workspace.

### Sistema de Permisos

#### 6. **Compartir Workspace**
```http
POST /api/workspaces/{workspace_id}/share
```
**Body:**
```json
{
    "email": "usuario@ejemplo.com",
    "role": "editor"
}
```

#### 7. **Listar Permisos**
```http
GET /api/workspaces/{workspace_id}/permissions
```
**Respuesta:**
```json
[
    {
        "account_id": "550e8400-e29b-41d4-a716-446655440000",
        "email": "propietario@ejemplo.com",
        "role": "owner"
    },
    {
        "account_id": "123e4567-e89b-12d3-a456-426614174000",
        "email": "colaborador@ejemplo.com",
        "role": "editor"
    }
]
```

#### 8. **Actualizar Permisos**
```http
PUT /api/workspaces/{workspace_id}/permissions/{account_id}
```
**Body:**
```json
{
    "new_role": "viewer"
}
```

#### 9. **Revocar Acceso**
```http
DELETE /api/workspaces/{workspace_id}/permissions/{account_id}
```

#### 10. **Verificar Mi Rol**
```http
GET /api/workspaces/{workspace_id}/my-role
```
**Respuesta:**
```json
{
    "role": "editor",
    "has_access": true
}
```

### Gestión de Contenido

#### 11. **Listar Items del Workspace**
```http
GET /api/workspaces/{workspace_id}/items
```
**Respuesta:** Combina tareas y eventos asociados al workspace:
```json
[
    {
        "id": "task-1",
        "type": "task",
        "description": "Implementar funcionalidad X",
        "status": "En Progreso"
    },
    {
        "id": "event-1", 
        "type": "event",
        "summary": "Reunión de equipo",
        "event_datetime_utc": "2025-12-23T15:00:00Z"
    }
]
```

## 🔒 Sistema de Permisos

### Verificación de Permisos

El sistema utiliza una dependencia centralizada para verificar permisos:

```python
from core.dependencies import check_workspace_permission

# En cualquier endpoint que requiera permisos
await check_workspace_permission(
    db=db,
    workspace_id=workspace_uuid,
    account_id=account_uuid,
    required_roles=['owner', 'editor']  # Roles requeridos
)
```

### Flujo de Permisos

1. **Creación**: El creador automáticamente obtiene rol `owner`
2. **Compartición**: Solo `owner` y `editor` pueden compartir
3. **Modificación**: Solo `owner` y `editor` pueden modificar
4. **Eliminación**: Solo `owner` puede eliminar
5. **Visualización**: Cualquier rol puede ver contenido

### Casos Especiales

- **Protección del Owner**: No se puede revocar el acceso del `owner` original
- **Búsqueda por Email**: Al compartir, se busca el usuario por su email
- **Validación de Roles**: Solo se permiten roles válidos (`owner`, `editor`, `viewer`)

## 💡 Casos de Uso

### 1. **Organización por Proyectos**
```
Workspace: "Desarrollo Web"
├── Tareas de desarrollo
├── Notas técnicas
├── Eventos de reuniones
└── Documentos del proyecto
```

### 2. **Gestión de Equipos**
```
Workspace: "Equipo Marketing"
├── Tareas colaborativas
├── Eventos de campaña
├── Notas de estrategia
└── Chats del equipo
```

### 3. **Separación de Contextos**
```
Workspace Personal: "Desarrollo Personal"
Workspace Profesional: "Proyecto Cliente A"
Workspace Aprendizaje: "Curso Python"
```

## 🛠️ Implementación Técnica

### Paginación
Los endpoints de listado utilizan paginación para optimizar rendimiento:
- Límite máximo: 100 elementos por página
- Parámetros: `skip` y `limit`
- Respuesta incluye `total` para navegación

### Validaciones
- **UUIDs**: Todos los IDs se validan como UUIDs válidos
- **Permisos**: Verificación automática en cada operación
- **Roles**: Validación de patrones para roles permitidos
- **Duplicados**: Prevención de permisos duplicados

### Manejo de Errores
```python
# Errores comunes y sus códigos HTTP
404 - Workspace no encontrado
403 - Permiso denegado
409 - Conflicto (usuario ya tiene acceso)
422 - Datos de entrada inválidos
```

### Transacciones
Todas las operaciones de base de datos utilizan transacciones para garantizar consistencia:
- Rollback automático en caso de error
- Commit explícito en operaciones exitosas

## 🔄 Flujo de Trabajo Típico

### 1. **Creación de Workspace**
```python
# 1. Usuario crea workspace
POST /api/workspaces
{
    "name": "Mi Proyecto",
    "color": "#007bff"
}

# 2. Sistema automáticamente:
# - Crea el workspace
# - Asigna rol 'owner' al creador
# - Registra timestamp de creación
```

### 2. **Compartir con Colaboradores**
```python
# 1. Owner o editor comparte workspace
POST /api/workspaces/{id}/share
{
    "email": "colaborador@empresa.com",
    "role": "editor"
}

# 2. Sistema busca usuario por email
# 3. Crea permiso si no existe
# 4. Confirma acceso
```

### 3. **Gestión de Contenido**
```python
# Crear contenido asociado al workspace
POST /api/tasks
{
    "description": "Nueva tarea",
    "workspace_id": "workspace-uuid"
}

# El contenido queda asociado y es visible
# solo para usuarios con acceso al workspace
```

## 📊 Métricas y Monitoreo

### Logging
El sistema registra operaciones importantes:
```python
logger.info(f"Workspace compartido con éxito con el usuario {invited_account_uuid} con el rol {request.role}.")
logger.error(f"Error al compartir workspace: {e}")
```

### Métricas Útiles
- Número de workspaces por usuario
- Frecuencia de compartición
- Distribución de roles
- Tiempo de creación de permisos

## 🚀 Mejores Prácticas

### Para Desarrolladores
1. **Siempre verificar permisos** antes de operaciones
2. **Usar UUIDs** en lugar de IDs numéricos
3. **Manejar errores** apropiadamente (404, 403, 409)
4. **Implementar paginación** en listados
5. **Validar roles** antes de asignar

### Para Usuarios
1. **Nombres descriptivos** para workspaces
2. **Colores distintivos** para fácil identificación
3. **Prompts específicos** para contexto de IA
4. **Gestión de permisos** regular
5. **Limpieza de accesos** innecesarios

## 🔧 Configuración Avanzada

### Personalización de Prompts
Cada workspace puede tener un prompt de sistema específico para la IA:

```json
{
    "name": "Asistente Legal",
    "system_prompt": "Eres un asistente legal especializado en derecho corporativo...",
    "color": "#6f42c1"
}
```

### Integración con IA
Los prompts específicos permiten:
- Contexto especializado por workspace
- Respuestas más precisas
- Mejor organización del conocimiento

## 📝 Consideraciones de Rendimiento

### Optimizaciones
- **Índices de base de datos** en campos frecuentemente consultados
- **Paginación** para evitar cargas grandes
- **Consultas optimizadas** con joins cuando sea necesario
- **Caché** de permisos frecuentes

### Límites del Sistema
- Máximo 100 workspaces por página
- Validación de permisos en cada operación
- Transacciones para consistencia de datos

---

## 📚 Referencias

- **Modelo de datos**: [`core/database.py`](core/database.py)
- **API endpoints**: [`api/workspaces.py`](api/workspaces.py)
- **Dependencias**: [`core/dependencies.py`](core/dependencies.py)
- **Ejemplos de uso**: Ver endpoints en la sección de API

---

*Documento actualizado: 22-12-2025*
*Versión del sistema: 1.0*