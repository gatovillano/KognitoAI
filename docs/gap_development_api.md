# Documentación de la API - Desarrollar Brecha

## Visión General

La API de Desarrollar Brecha permite a los usuarios iniciar investigaciones profundas sobre brechas de conocimiento y obtener informes estructurados. Esta API está diseñada para ser utilizada por roles de `analyst` y `admin`.

## Autenticación

Todas las solicitudes requieren autenticación mediante JWT. Incluya el token en el encabezado:

```
Authorization: Bearer {token}
```

## Endpoints

### 1. Iniciar Investigación de Brecha

**POST** `/api/gap-development/`

Inicia una investigación profunda sobre una brecha de conocimiento específica.

**Parámetros de entrada:**

```json
{
  "gap_id": "string (UUID)",  // ID de la brecha de conocimiento
  "context": "string (opcional)",  // Contexto adicional para la investigación
  "depth": "integer (opcional)"  // Profundidad de la investigación (1-5, default: 3)
}
```

**Respuesta exitosa (200):**

```json
{
  "status": "pending",
  "gap_id": "string",
  "analysis_id": "string",
  "message": "Analysis started successfully"
}
```

**Posibles estados:**
- `pending`: El análisis ha sido creado y está esperando procesamiento
- `processing`: El análisis está en progreso
- `completed`: El análisis ha finalizado con éxito
- `failed`: El análisis falló

**Errores comunes:**
- `403 Forbidden`: Usuario no tiene permisos (solo roles `analyst`/`admin`)
- `404 Not Found`: Brecha de conocimiento no encontrada
- `500 Internal Server Error`: Error en el servidor

**Ejemplo de uso:**

```bash
curl -X POST /api/gap-development/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {token}" \
  -d '{
    "gap_id": "550e8400-e29b-41d4-a716-446655440000",
    "context": "Investigar sobre inteligencia artificial en salud",
    "depth": 3
  }'
```

### 2. Obtener Estado del Análisis

**GET** `/api/gap-development/{analysis_id}`

Obtiene el estado actual y resultados de un análisis específico.

**Parámetros de URL:**
- `analysis_id`: ID del análisis (UUID)

**Respuesta exitosa (200):**

```json
{
  "status": "completed",
  "gap_id": "string",
  "analysis_id": "string",
  "report": {
    "summary": "string",
    "findings": ["string"],
    "sources": [
      {
        "url": "string",
        "relevance": "number (0-10)"
      }
    ],
    "recommendations": ["string"]
  },
  "error": "string (opcional)"
}
```

**Errores comunes:**
- `403 Forbidden`: Usuario no tiene permisos
- `404 Not Found`: Análisis no encontrado o no tiene permisos para acceder

**Ejemplo de uso:**

```bash
curl -X GET /api/gap-development/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer {token}"
```

### 3. Obtener Análisis por ID de Brecha

**GET** `/api/gap-development/by-gap/{gap_id}`

Obtiene el análisis más reciente para una brecha de conocimiento específica.

**Parámetros de URL:**
- `gap_id`: ID de la brecha de conocimiento (UUID)

**Respuesta exitosa (200):**

```json
{
  "status": "completed",
  "gap_id": "string",
  "analysis_id": "string",
  "report": {
    "summary": "string",
    "findings": ["string"],
    "sources": [
      {
        "url": "string",
        "relevance": "number (0-10)"
      }
    ],
    "recommendations": ["string"]
  },
  "error": "string (opcional)"
}
```

**Errores comunes:**
- `403 Forbidden`: Usuario no tiene permisos
- `404 Not Found`: No se encontró análisis para esta brecha

**Ejemplo de uso:**

```bash
curl -X GET /api/gap-development/by-gap/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer {token}"
```

## WebSocket Notifications

La API envía notificaciones en tiempo real mediante WebSocket cuando el estado de un análisis cambia.

**Tipo de mensaje:** `gap_development_update`

**Estructura del mensaje:**

```json
{
  "type": "gap_development_update",
  "status": "pending|processing|completed|failed",
  "analysis_id": "string",
  "gap_id": "string",
  "message": "string",
  "report": "object (opcional, solo en completed)",
  "error": "string (opcional, solo en failed)",
  "question": "string (opcional, si se necesita clarificación)"
}
```

**Ejemplo de mensaje:**

```json
{
  "type": "gap_development_update",
  "status": "completed",
  "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
  "gap_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Analysis completed successfully",
  "report": {
    "summary": "Resumen del informe...",
    "findings": ["Hallazgo 1", "Hallazgo 2"],
    "sources": [
      {
        "url": "https://example.com",
        "relevance": 8.5
      }
    ],
    "recommendations": ["Recomendación 1", "Recomendación 2"]
  }
}
```

## Estructura del Informe

El informe generado por el análisis tiene la siguiente estructura:

```json
{
  "summary": "Resumen ejecutivo del análisis (máx. 500 caracteres)",
  "findings": [
    "Hallazgo detallado 1",
    "Hallazgo detallado 2",
    "..."
  ],
  "sources": [
    {
      "url": "URL de la fuente",
      "relevance": "Puntuación de relevancia (0-10)"
    }
  ],
  "recommendations": [
    "Recomendación 1",
    "Recomendación 2",
    "..."
  ]
}
```

## Manejo de Errores

La API sigue estándares REST para el manejo de errores:

- `400 Bad Request`: Parámetros inválidos
- `401 Unauthorized`: Token no proporcionado o inválido
- `403 Forbidden`: Usuario no tiene permisos
- `404 Not Found`: Recurso no encontrado
- `500 Internal Server Error`: Error interno del servidor

**Ejemplo de respuesta de error:**

```json
{
  "detail": "Only users with 'analyst' or 'admin' roles can use this feature."
}
```

## Limitaciones y Consideraciones

1. **Tiempo de procesamiento**: Los análisis pueden tomar entre 30 y 120 segundos
2. **Roles requeridos**: Solo usuarios con roles `analyst` o `admin` pueden usar esta API
3. **Concurrencia**: Se permite solo un análisis en progreso por brecha de conocimiento
4. **Almacenamiento**: Los resultados se almacenan por 30 días
5. **Tamaño máximo**: El informe completo no debe exceder 10MB

## Ejemplo de Flujo Completo

1. **Iniciar análisis:**
   ```bash
   POST /api/gap-development/
   ```

2. **Recibir notificación WebSocket:**
   ```json
   {
     "type": "gap_development_update",
     "status": "processing",
     "analysis_id": "...",
     "message": "Analysis started"
   }
   ```

3. **Consultar estado (opcional):**
   ```bash
   GET /api/gap-development/{analysis_id}
   ```

4. **Recibir notificación de completado:**
   ```json
   {
     "type": "gap_development_update",
     "status": "completed",
     "analysis_id": "...",
     "report": { ... }
   }
   ```

5. **Visualizar resultados en la interfaz de usuario**

## Integración con Frontend

El frontend debe:
1. Mostrar el botón "Desarrollar" solo para usuarios con roles adecuados
2. Manejar el diálogo de confirmación antes de iniciar
3. Mostrar indicadores de progreso durante el procesamiento
4. Escuchar notificaciones WebSocket para actualizar la UI en tiempo real
5. Mostrar los resultados en pestañas (Resumen, Hallazgos, Fuentes, Recomendaciones)
6. Proporcionar opciones para exportar, guardar y compartir los resultados

## Seguridad

- Todos los endpoints requieren autenticación JWT
- Validación de roles en el backend
- Los usuarios solo pueden acceder a sus propios análisis
- Protección CSRF en formularios
- Rate limiting: máximo 5 solicitudes por minuto por usuario

## Versión de la API

**Versión actual:** 1.0.0

**Changelog:**
- 1.0.0: Versión inicial con funcionalidad básica de análisis
- 1.0.1: Añadido soporte para WebSocket notifications
- 1.0.2: Mejorado manejo de errores y validaciones

## Soporte

Para problemas o preguntas, contacte al equipo de desarrollo:
- Email: support@kognito.ai
- Documentación: https://docs.kognito.ai/gap-development
- API Status: https://status.kognito.ai

## Ejemplo de Código (Frontend)

```typescript
// Iniciar análisis
const startAnalysis = async (gapId: string) => {
  const response = await fetch('/api/gap-development/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      gap_id: gapId,
      context: 'Contexto adicional',
      depth: 3
    })
  });
  
  if (response.ok) {
    const data = await response.json();
    console.log('Analysis started:', data);
  }
};

// Escuchar WebSocket
socket.on('message', (message) => {
  if (message.type === 'gap_development_update') {
    console.log('Status update:', message);
    // Actualizar UI según el estado
  }
});
```

## Pruebas

**Endpoint de prueba:**
```bash
GET /api/gap-development/test
```

**Respuesta:**
```json
{
  "message": "Gap Development API is working correctly",
  "version": "1.0.0",
  "status": "operational"
}
```

## Depuración

Para depurar problemas:
1. Verifique los logs del servidor
2. Asegúrese de que el token JWT sea válido
3. Verifique que el usuario tenga el rol correcto
4. Confirme que la brecha de conocimiento exista
5. Revise la conexión WebSocket

**Logs útiles:**
- `/var/log/kognito/api.log`
- `/var/log/kognito/websocket.log`
- `/var/log/kognito/celery.log` (si aplica)

## Métricas

La API registra las siguientes métricas:
- Tiempo promedio de procesamiento
- Número de análisis por usuario
- Tasa de éxito/fallo
- Uso de recursos

Estas métricas están disponibles en el panel de administración.