--- 
## 22-10-25 Corrección: Rutas de Notas en Frontend (src y Telegram Panel)

Se corrigió la inconsistencia en las rutas de la API para las notas en el frontend, tanto en la aplicación principal (`src/app/(dashboard)/notes/edit/[id]/page.tsx`) como en el panel de Telegram (`telegram_panel/script.js`). Esto resuelve el problema de que las notas no cargaban después de la reversión en el backend.

- **Punto 1**: En `telegram_panel/script.js`, se modificaron las llamadas a la API para añadir, actualizar y eliminar notas para que incluyan el prefijo `/notes`. Específicamente, se cambió `'/api/add-note'` a `'/api/notes/add-note'`, `'/api/update-note'` a `'/api/notes/update-note'`, y `'/api/delete-note'` a `'/api/notes/delete-note'`.
- **Punto 2**: En `src/app/(dashboard)/notes/edit/[id]/page.tsx`, se modificaron las llamadas a la API para añadir, actualizar y auto-guardar notas para que incluyan el prefijo `/notes`. Específicamente, se cambió `'/api/update-note'` a `'/api/notes/update-note'` en la función `autoSaveNote`, y `'/api/add-note'` a `'/api/notes/add-note'` y `'/api/update-note'` a `'/api/notes/update-note'` en la función `handleSave`.
---
## 22-10-25 Corrección: Carga de Notas Vacías en el Editor

Se corrigió un problema en `src/app/(dashboard)/notes/edit/[id]/page.tsx` donde las notas se cargaban vacías, lo que provocaba la pérdida de contenido debido al autoguardado.

- **Punto 1**: Se ajustó la lógica de carga de notas personales para asegurar que la respuesta de la API se maneje correctamente. Ahora, cuando se intenta obtener una nota directamente por ID, se asigna el `data` de la respuesta a una variable y se verifica su contenido antes de establecer el estado de la nota.
- **Punto 2**: Se corrigió un `console.log` en la sección de fallback para que muestre los datos correctos (`fallbackResponse.data`) en lugar de una variable incorrecta (`response.data`).
---
## 22-10-25 Corrección: Error 500 al Cargar Nota por ID en Backend

Se corrigió un error 500 en el backend al intentar cargar una nota por su ID. El problema se debía a que el método `get_note_by_id` en `core/notes_manager.py` no devolvía los campos `workspace_name` y `workspace_color`, que eran esperados por el modelo `NoteResponse` en `api/notes.py`.

- **Punto 1**: Se modificó el método `get_note_by_id` en `core/notes_manager.py` para incluir `workspace_name` y `workspace_color` en el diccionario que devuelve, asegurando que la estructura de datos coincida con la esperada por el frontend y el modelo Pydantic.
---
## 22-10-25 Corrección: Notificación "Contenido no disponible" en el Editor de Notas

Se abordó la aparición de la notificación "El contenido de la nota no está disponible" en el frontend, que ocurría incluso después de corregir el error 500 del backend. Se determinó que la lógica del frontend realizaba una llamada redundante a la API para obtener el contenido de la nota.

- **Punto 1**: Se eliminó la segunda llamada a la API en `src/app/(dashboard)/notes/edit/[id]/page.tsx` que intentaba cargar el contenido completo de la nota. Ahora, si el `content` de la nota está vacío después de la carga inicial, se asume que la nota no tiene contenido y se muestra el mensaje de error correspondiente, evitando llamadas innecesarias al backend.
---
## 22-10-2025 Mejora: Integración de Vista Semanal de Agenda en Workspace

Se ha integrado la vista semanal de la agenda (`WeeklyScheduleView`) en la página de detalles del workspace (`src/app/(dashboard)/workspaces/[id]/page.tsx`). Esto permite visualizar y gestionar eventos y tareas de calendario directamente desde el dashboard del workspace, ofreciendo una experiencia de usuario más completa y organizada.

- **Punto 1**: Se importó el componente `WeeklyScheduleView` de `src/app/(dashboard)/agenda/WeeklyScheduleView.tsx` en `src/app/(dashboard)/workspaces/[id]/page.tsx`.
- **Punto 2**: Se añadió el estado `currentDate` y las funciones de manejo (`handleEditEvent`, `handleDeleteEvent`, `handleEditTask`, `handleDeleteTask`, `handleToggleTaskCompleted`) en `src/app/(dashboard)/workspaces/[id]/page.tsx` para gestionar la interacción con el calendario y los elementos de la agenda.
- **Punto 3**: Se reemplazó la sección anterior de "Agenda del Workspace" con el componente `WeeklyScheduleView`, pasándole los eventos y tareas existentes, así como las funciones de manejo correspondientes.
- **Punto 4**: Se modificaron los componentes `EventDialog` y `TaskDialog` para que reciban el evento o tarea seleccionada como prop, permitiendo la edición de elementos existentes.
---
## 22-10-2025 Corrección: TypeError en GetDocumentListTool por argumento 'team_id' inesperado

Se corrigió un `TypeError` en `GetDocumentListTool` que ocurría porque la función `list_user_documents()` estaba recibiendo un argumento `team_id` inesperado. La función `list_user_documents()` no tiene `team_id` en su firma, lo que provocaba el error.

- **Punto 1**: Se eliminó el argumento `team_id` de la llamada a `list_user_documents()` en `tools/get_document_list_tool.py` para que solo se pasen los parámetros esperados por la función.