# Diseño de Analíticas de Actividad de Usuarios y Uso de Funciones

## Contexto y Objetivo
El objetivo de este sistema es proporcionar a los administradores de KognitoAI visibilidad completa sobre el uso de la plataforma por parte de los usuarios. Permite identificar cuándo se conectó por última vez cada usuario, su nivel de actividad reciente y qué módulos o funciones (Chat, Notas, Formularios, Mapas Mentales, Grafos de Conocimiento, etc.) utilizan con mayor frecuencia.

---

## 1. Modelo de Datos (`core/database.py`)

Se extienden los atributos del modelo `Account` para registrar explícitamente la presencia y conectividad de los usuarios:

- **`last_login_at`**: `Column(DateTime(timezone=True), nullable=True, comment="Fecha y hora de inicio de sesión")`
- **`last_active_at`**: `Column(DateTime(timezone=True), nullable=True, comment="Fecha y hora de última actividad/evento registrado")`

### Script de Migración
Se incluirá un script ejecutable (`add_user_activity_columns.py`) utilizando SQLAlchemy `ALTER TABLE accounts ADD COLUMN ...` para asegurar la compatibilidad sin interrumpir la base de datos existente.

---

## 2. Lógica Backend y Endpoints API (`api/`)

### Actualización Automática de Timestamps
1. **Inicio de Sesión**: En los flujos de autenticación (`api/users.py`), al generar o entregar un token válido se actualiza `account.last_login_at = func.now()`.
2. **Rastreo de Actividad (`api/analytics.py`)**: Cuando el endpoint `/api/analytics/track` recibe una petición autenticada (`account_id` presente), se actualiza `account.last_active_at = func.now()`.

### Mapeo de Funciones por Ruta (`path`)
Los eventos de analítica almacenan la ruta (`path`). Se implementa una utilidad de mapeo para convertir rutas en nombres de funciones amigables:
- `/chat` o `/c/*` $\rightarrow$ **Asistente de Chat**
- `/notes` o `/notas` $\rightarrow$ **Gestor de Notas**
- `/forms` o `/formularios` $\rightarrow$ **Formularios Dinámicos**
- `/mindmap` $\rightarrow$ **Mapas Mentales**
- `/knowledge-graph` o `/grafo` $\rightarrow$ **Grafo de Conocimiento**
- `/settings` o `/perfil` $\rightarrow$ **Configuración y Perfil**
- Otros $\rightarrow$ Categorizados según prefijo de ruta.

### Nuevos Endpoints en API

#### `GET /api/admin/analytics/users`
**Respuesta:**
```json
{
  "users": [
    {
      "account_id": "uuid-string",
      "name": "Juan Pérez",
      "email": "juan@ejemplo.com",
      "username": "juanp",
      "is_admin": false,
      "last_login_at": "2026-08-01T18:45:00Z",
      "last_active_at": "2026-08-01T19:02:11Z",
      "total_events": 142,
      "status": "online", // online (<15m), active (<24h), inactive (>24h), never
      "top_features": [
        { "name": "Asistente de Chat", "count": 85, "percentage": 60 },
        { "name": "Gestor de Notas", "count": 35, "percentage": 25 },
        { "name": "Mapas Mentales", "count": 22, "percentage": 15 }
      ]
    }
  ]
}
```

#### `GET /api/admin/analytics/features`
Devuelve el conteo general y porcentaje de uso de cada función en toda la plataforma agrupado por período (`24h`, `7d`, `30d`, `all`).

---

## 3. Interfaz de Usuario Administrador (`src/app/(dashboard)/admin/analytics/page.tsx`)

Se amplía el tablero de analíticas existente agregando una vista estructurada:

1. **Pestañas de Navegación**:
   - **Tráfico General** (Analíticas web y navegadores existentes)
   - **Usuarios y Funciones** (Nueva sección)
2. **Componentes en "Usuarios y Funciones"**:
   - **Tarjetas Resumen**:
     - Usuarios Activos Hoy
     - Conexiones en las últimas 24h
     - Función Más Utilizada globalmente
   - **Tabla de Usuarios**:
     - Filtro por nombre/email.
     - Indicador de estado (Punto verde: En línea, Amarillo: Hoy, Gris: Inactivo).
     - Columnas: Usuario, Email, Última Conexión, Última Actividad, Total Acciones, Funciones Principales (Badges con icono y porcentaje).
   - **Gráfico de Funciones Globales**:
     - Gráfico de Barras horizontales / Pie Chart mostrando el desglose de uso de cada módulo del sistema.

---

## 4. Plan de Verificación
1. **Base de Datos**: Verificar la adición de columnas mediante script y comprobar la persistencia de `last_login_at` y `last_active_at`.
2. **Endpoints API**: Probar `/api/admin/analytics/users` y `/api/admin/analytics/features` verificando la exactitud del cálculo de las funciones principales.
3. **Frontend**: Verificar la renderización en Next.js, filtros de búsqueda y formato correcto de fechas e insignias de funciones.
