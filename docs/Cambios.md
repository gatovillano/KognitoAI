## 03-10-25 Corrección de Rutas de API en Workspace Dashboard

Se corrigieron las rutas de las llamadas a la API en el componente `WorkspaceDashboard` (`src/app/(dashboard)/workspaces/[id]/page.tsx`) para que coincidieran con las rutas definidas en el backend, resolviendo errores 404.

- **Ajuste de ruta para `list-notes`**: Se cambió la llamada a `apiClient.post('/api/list-notes', ...)` a `apiClient.post('/api/notes/list-notes', ...)` en las líneas 110 y 108.
- **Ajuste de ruta para `collections`**: Se cambió la llamada a `apiClient.get('/api/collections?...')` a `apiClient.get('/api/documents/collections?...')` en las líneas 107, 264 y 299.

---

## 03-10-25 Filtrado de Eventos por Workspace en Backend y Frontend

Se implementó el filtrado de eventos por `workspace_id` en el backend y se eliminó el filtrado redundante en el frontend para asegurar que solo se muestren los eventos relevantes para cada workspace.

- **Modificación de `ListEventsRequest` en `api/agenda.py`**: Se añadió el campo `workspace_id: Optional[str] = None` al modelo `ListEventsRequest` en la línea 72.
- **Modificación de `list_events_endpoint` en `api/agenda.py`**: Se ajustó la lógica del endpoint `list_events_endpoint` (línea 74) para que, si se proporciona un `workspace_id` en la solicitud, solo se obtengan y devuelvan los eventos asociados a ese `workspace_id`.
- **Ajuste en `src/app/(dashboard)/workspaces/[id]/page.tsx`**: Se eliminó el filtrado del lado del cliente (`.filter((event: AgendaEvent) => event.workspace_id === workspaceId)`) en la línea 115, ya que el backend ahora se encarga de enviar solo los eventos pertinentes.

---

## 03-10-25 Corrección de Prefijo de Router para Documentos

Se corrigió la inclusión del `documents_router` en `api/main.py` para asegurar que las rutas de colecciones se construyan correctamente.

- **Ajuste en `api/main.py`**: Se modificó la inclusión del `documents_router` de `app.include_router(documents_router, prefix="/api", tags=["documents"])` a `app.include_router(documents_router, prefix="/api/documents", tags=["documents"])` en la línea 187.