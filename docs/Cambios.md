## 10-08-25 Mejora de UI en Menú de Acciones de Agenda para Móviles

Descripción general: Se ajustó el menú de "Acciones" en la página de Agenda (`src/app/(dashboard)/agenda/page.tsx`) para que en dispositivos móviles solo se muestre el icono de tres puntos, ocultando el texto "Acciones", optimizando el espacio y la estética.

- **Punto 1**: Se modificó el componente `DropdownMenuTrigger` para que el texto "Acciones" (`<span>Acciones</span>`) se oculte en pantallas pequeñas (`hidden`) y solo sea visible a partir de un tamaño de pantalla mediano (`md:inline`).
- **Punto 2**: Se ajustó el padding del botón del `DropdownMenuTrigger` (`px-2 md:px-4`) para una mejor apariencia en diferentes tamaños de pantalla.
- **Punto 3**: Se añadió un margen condicional al icono `MoreHorizontal` (`md:ml-2`) para mantener la alineación en pantallas más grandes.
---
## 11-08-25 Mejora de Responsividad en Colecciones de Documentos para Móviles

Descripción general: Se realizaron ajustes en el componente `DocumentCollectionDisplay.tsx` para mejorar su adaptabilidad y responsividad en pantallas móviles, asegurando una mejor experiencia de usuario.

- **Punto 1**: Se modificó el contenedor principal del título y los botones de acción para que se apilen verticalmente en pantallas pequeñas (`flex-col`) y se mantengan en fila en pantallas medianas y grandes (`sm:flex-row`), añadiendo un `gap-4` para espaciado.
- **Punto 2**: Se eliminó la clase `flex-grow` de la primera `Card` y se envolvieron ambas tarjetas (`Documentos en la Colección` e `Historial de Análisis`) en un nuevo `div` con `space-y-6` para asegurar un espaciado vertical consistente.
- **Punto 3**: Se cambió `overflow-auto` a `overflow-x-auto` en el contenedor de la `DataTable` para permitir el desplazamiento horizontal solo cuando sea necesario, mejorando la visualización de tablas grandes en pantallas pequeñas.
---
## 11-08-25 Mejora de Responsividad General en Componentes RAG para Móviles

Descripción general: Se realizaron ajustes de responsividad en varios componentes dentro del directorio `src/app/(dashboard)/rag/` para asegurar una óptima visualización y experiencia de usuario en dispositivos móviles.

- **analysis-result-dialog.tsx**: Se ajustó el `DialogContent` principal para ocupar el ancho completo en móviles (`w-full`) y se controló el `max-w` en pantallas más grandes. Se aumentó la altura del `ScrollArea` en móviles (`h-[70vh] sm:h-[60vh]`) y se ajustaron los diálogos secundarios de temas para ser más responsivos (`max-w-lg w-full`).
- **code-analysis-result-dialog.tsx**: Se modificó el `DialogContent` para un ancho completo en móviles (`w-full`) y se ajustó el `max-w` para pantallas grandes. Se reorganizó el `TabsList` para mostrar menos columnas en móviles (`grid-cols-1 sm:grid-cols-2 md:grid-cols-3`) y se aumentó la altura del `ScrollArea` (`h-[70vh] sm:h-[60vh]`).
- **collection-analysis-dialog.tsx**: Se ajustó el `DialogContent` principal (`max-w-5xl w-full`) y se hizo el `DialogTitle` responsivo. Se modificó el `TabsList` para adaptarse a diferentes columnas en móviles (`grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-8`) y se aumentó la altura del `ScrollArea` (`h-[70vh] sm:h-[65vh] md:h-[60vh]`). Los diálogos secundarios también se hicieron más responsivos (`max-w-lg w-full`). Se eliminó una importación no utilizada de `TTSButton`.
- **columns.tsx**: Se hicieron las columnas `file_name` y `topic` condicionalmente visibles, ocultándose en pantallas pequeñas (`hidden sm:table-cell` y `hidden md:table-cell` respectivamente) para optimizar el espacio en la tabla.
- **create-collection-dialog.tsx**: Se ajustó el `DialogContent` (`max-w-md w-full`) y el `DialogTitle` para responsividad. El `Select` de equipo se configuró para ocupar todo el ancho (`w-full`) y el `DialogFooter` se hizo responsivo (`flex-col-reverse sm:flex-row`).
- **custom-analysis-dialog.tsx**: Se ajustó el `DialogContent` (`max-w-xl w-full`) y el `DialogTitle` para responsividad. El `DialogFooter` se hizo responsivo (`flex-col-reverse sm:flex-row`), y los botones dentro del `DialogFooter` también se adaptaron al ancho completo en móviles (`w-full sm:w-auto`).
- **data-table.tsx**: Se añadió la clase `min-w-full` a la `Table` para asegurar que ocupe todo el ancho disponible y se permitan los scrolls horizontales. Se aplicó `whitespace-nowrap` a `TableHead` y `TableCell` para evitar saltos de línea y forzar el scroll horizontal.
- **delete-confirmation-dialog.tsx**: Se ajustó el `AlertDialogContent` (`max-w-md w-full`) y el `AlertDialogTitle` para responsividad. El `AlertDialogFooter` se hizo responsivo (`flex-col-reverse sm:flex-row`) y los botones (`AlertDialogCancel`, `AlertDialogAction`) se adaptaron al ancho completo en móviles (`w-full sm:w-auto`).
- **edit-collection-dialog.tsx**: Se ajustó el `DialogContent` (`max-w-md w-full`) y el `DialogTitle` para responsividad. El `DialogFooter` se hizo responsivo (`flex-col-reverse sm:flex-row`) y los botones (`Cancelar`, `Guardar Cambios`) se adaptaron al ancho completo en móviles (`w-full sm:w-auto`).
- **edit-document-dialog.tsx**: Se ajustó el `DialogContent` (`max-w-md w-full`) y el `DialogTitle` para responsividad. El `DialogFooter` se hizo responsivo (`flex-col-reverse sm:flex-row`) y los botones (`Guardar Cambios`, `Cancelar`) se adaptaron al ancho completo en móviles (`w-full sm:w-auto`).
- **github-repo-dialog.tsx**: Se ajustó el `DialogContent` (`max-w-md w-full`) y el `DialogTitle` para responsividad. El `SelectTrigger` se configuró para ocupar todo el ancho (`w-full`) y el `DialogFooter` se hizo responsivo (`flex-col-reverse sm:flex-row`) con botones adaptados al ancho completo en móviles (`w-full sm:w-auto`).
- **preview-document-dialog.tsx**: Se ajustó el `DialogContent` (`max-w-4xl w-full h-[90vh] sm:h-[80vh]`) y el `DialogTitle` para responsividad.
- **semantic-analysis-dialog.tsx**: Se ajustó el `DialogContent` principal (`max-w-5xl w-full`) y los diálogos secundarios de temas y conceptos (`max-w-lg w-full`) para responsividad, incluyendo la altura máxima y el padding. El `ScrollArea` principal aumentó su altura (`h-[75vh] sm:h-[70vh]`) y se ajustaron las columnas de estadísticas (`grid-cols-2 sm:grid-cols-3 md:grid-cols-4`). El `DialogFooter` también se hizo responsivo (`flex-col-reverse sm:flex-row`).
- **share-collection-dialog.tsx**: Se ajustó el `DialogContent` (`max-w-md w-full`) y el `DialogTitle` para responsividad. El `SelectTrigger` se configuró para ocupar todo el ancho (`w-full`) y el `DialogFooter` se hizo responsivo (`flex-col-reverse sm:flex-row`) con botones adaptados al ancho completo en móviles (`w-full sm:w-auto`).
- **share-document-dialog.tsx**: Se ajustó el `DialogContent` (`max-w-md w-full`) y el `DialogTitle` para responsividad. El `SelectTrigger` se configuró para ocupar todo el ancho (`w-full`) y el `DialogFooter` se hizo responsivo (`flex-col-reverse sm:flex-row`) con botones adaptados al ancho completo en móviles (`w-full sm:w-auto`).
- **update-repository-dialog.tsx**: Se ajustó el `DialogContent` (`max-w-md w-full`) y el `DialogTitle` para responsividad. El `DialogFooter` se hizo responsivo (`flex-col-reverse sm:flex-row`) y todos los botones dentro del `DialogFooter` se adaptaron al ancho completo en móviles (`w-full sm:w-auto`).
- **upload-document-dialog.tsx**: Se ajustó el `DialogContent` (`max-w-xl w-full`) y el `DialogTitle` para responsividad. La altura del `TiptapEditor` se hizo responsiva (`max-h-[250px] sm:max-h-60`) y el `DialogFooter` se hizo responsivo (`flex-col-reverse sm:flex-row`) con botones adaptados al ancho completo en móviles (`w-full sm:w-auto`).
---
## 12-08-25 Ajuste de columnas en la vista de notas por categoría
Descripcion general: El usuario solicitó ajustar el número de columnas en la vista de notas por categoría de 4 a 3. Se modificó el archivo @src/app/(dashboard)/notes/page.tsx para corregir el layout.
- **Punto 1**: Se modificó el archivo `/home/gato/KognitoAI/kognito-ai/src/app/(dashboard)/notes/page.tsx` para cambiar la clase `xl:grid-cols-4` por `xl:grid-cols-3` en el componente `CategoryDropZone`.
---
## 12-08-25 Mejora de UI en la página de Colecciones de Conocimiento
Descripción general: Se eliminó la descripción de texto debajo del título principal en la página de Colecciones de Conocimiento (`@src/app/(dashboard)/rag/page.tsx`) y se movió el ícono de información para que aparezca junto al título, logrando una interfaz más limpia.
- **Punto 1**: Se refactorizó el JSX en `/home/gato/KognitoAI/kognito-ai/src/app/(dashboard)/rag/page.tsx` para eliminar el párrafo de descripción.
- **Punto 2**: El componente `TooltipProvider` que contiene el ícono de información fue movido dentro de la etiqueta `<h1>` del título para asegurar que el ícono se muestre alineado y junto al texto del título.
---
## 12-08-25 Corrección de ValidationError en GitHubRepoTool

Descripción general: Se identificó y resolvió un `ValidationError` en la [`GitHubRepoTool`](/app/tools/github_repo_tool.py:71) debido a la ausencia del `account_id` en su constructor. La solución consistió en asegurar el correcto suministro del `account_id` y el paso adecuado de argumentos en las llamadas a los métodos de la herramienta en [`api/github.py`](api/github.py).

- **Problema de `ValidationError`**: El `account_id` no se estaba suministrando al constructor de `GitHubRepoTool`, lo que provocaba un error de validación.
- **Solución en `GitHubRepoTool`**: Se modificó el constructor de `GitHubRepoTool` para que aceptara y utilizara el `account_id`.
- **Ajustes en `api/github.py`**: Se aseguró que el `account_id` se pasara correctamente al constructor de `GitHubRepoTool` y que los argumentos se transfirieran adecuadamente en las llamadas a los métodos `_arun` y `_update_knowledge_collection` de la herramienta.
---
## 12-08-25 Corrección en la adición de repositorios de GitHub para evitar la vectorización

Descripción general: Se corrigió un problema en el que al añadir un repositorio de GitHub, su contenido se vectorizaba incorrectamente en lugar de solo guardarse como texto. El frontend ya enviaba la instrucción de no vectorizar (`vectorize: false`), pero el backend la ignoraba.

- **Punto 1**: Se modificó el modelo `GitHubCollectionRequest` en `api/github.py` para incluir el campo `vectorize: Optional[bool] = True`, permitiendo que la solicitud del frontend sea procesada correctamente.
- **Punto 2**: Se actualizó la función `manage_github_collection` en `api/github.py` para que utilice el valor de `request.vectorize` al llamar a la herramienta `github_tool._arun`, asegurando que la preferencia de no vectorizar sea respetada por el backend.
---
## 12-08-2025 Corrección de previsualización de documentos de GitHub no vectorizados
Descripción general: Se solucionó un problema donde el botón "previsualizar" en documentos de GitHub intentaba buscar contenido en la base de datos vectorial, lo cual fallaba para documentos no vectorizados.
- **Problema**: La función `get_full_document_content` solo consultaba la tabla `langchain_pg_embedding` (para documentos vectorizados), ignorando los documentos de GitHub almacenados en `GitHubDocument`.
- **Solución**: Se modificó el endpoint `/api/get-document-content` en `api/documents.py` para que primero intente recuperar el contenido del documento desde la tabla `GitHubDocument`. Si el documento es de GitHub y se encuentra allí, se devuelve su contenido directamente. De lo contrario, se recurre a la búsqueda en la base de datos vectorial.
- **Impacto**: Los usuarios ahora pueden previsualizar correctamente el contenido de los documentos de GitHub, independientemente de si han sido vectorizados o no.
---
## 12-08-2025 Corrección de `NameError` en `api/documents.py`
Descripción general: Se resolvió un `NameError` en `api/documents.py` debido a la falta de importación de `get_db_session`.
- **Problema**: La función `get_document_content_endpoint` en `api/documents.py` utilizaba `get_db_session` sin que esta función estuviera importada o definida en el archivo.
- **Solución**: Se añadió `get_db_session` a la declaración de importación de `core.database` en `api/documents.py`.
- **Impacto**: Se eliminó el error de tiempo de ejecución, permitiendo que el endpoint `get-document-content` funcione correctamente.
---
## 12-08-2025 Mejora de UI y Funcionalidad de Eliminación en Repositorios de GitHub

Descripción general: Se mejoró la interfaz de usuario en la página de detalles de repositorios de GitHub (`src/app/(dashboard)/rag/repositories/[repoName]/page.tsx`) al consolidar los botones de acción en menús desplegables. Además, se implementó la funcionalidad completa para eliminar archivos y carpetas de la base de conocimiento de la IA, asegurando que los cambios se reflejen correctamente en la UI y en las bases de datos relevantes.

- **Punto 1**: **Frontend (`src/app/(dashboard)/rag/repositories/[repoName]/page.tsx`)**:
    - Se corrigió la función `onDeleteSuccess` del `DeleteConfirmationDialog` para que recargue los documentos después de eliminar un archivo, asegurando la actualización de la UI.
    - Se implementó la función `handleDeleteFolder` para manejar la eliminación de carpetas, llamando a la nueva API de backend.
    - Se modificó el botón de eliminar carpeta para que utilice `handleDeleteFolder`.
    - Se corrigió la ubicación de la función `refreshDocuments` para asegurar su correcto ámbito y accesibilidad.
    - Se restauró la declaración de la variable de estado `savedAnalyses`, que había sido eliminada accidentalmente.
    - Se añadió el componente `DocumentActionsDropdown` para los documentos individuales, encapsulando las acciones de ver, editar, analizar, compartir y eliminar.
    - Se reemplazaron los botones individuales de los documentos por el nuevo `DocumentActionsDropdown`.
    - Se consolidaron los botones "Actualizar Repositorio", "Analizar Repositorio" y "Vectorizar Repositorio" en un único `DropdownMenu` para una interfaz más limpia.
    - Se añadió `ChevronDown` a las importaciones de `lucide-react` para resolver un error de "not defined".
    - Se cambió el texto del botón del menú de acciones del repositorio a simplemente "Acciones".
- **Punto 2**: **Backend (`core/memory_manager.py`)**:
    - Se modificó la función `delete_document_chunks` para que acepte un nuevo parámetro `file_name_prefix`. Esto permite eliminar eficientemente todos los documentos cuyo nombre de archivo comience con un prefijo específico (útil para eliminar contenidos de carpetas).
    - Se añadió la importación de la tabla `GitHubDocument` para permitir la manipulación de estos registros.
    - Se implementó la lógica dentro de `delete_document_chunks` para eliminar los registros correspondientes tanto de la base de datos vectorial (`langchain_pg_embedding`) como de la tabla `GitHubDocument`, asegurando una eliminación completa de la base de conocimiento de la IA.
- **Punto 3**: **Backend (`api/documents.py`)**:
    - Se añadió un nuevo endpoint POST `/api/github/delete-folder` que recibe el nombre del repositorio y la ruta de la carpeta. Este endpoint utiliza la función `delete_document_chunks` (con el nuevo parámetro `file_name_prefix`) para eliminar todos los documentos y sus chunks asociados dentro de la carpeta especificada.
---
## 12-08-2025 Corrección de `ValidationError` en `AddWebToRAGTool`

Descripción general: Se resolvió un `ValidationError` en `AddWebToRAGTool` debido a la ausencia del `account_id` en su inicialización.

- **Punto 1**: Se modificó la inicialización de `AddWebToRAGTool` en `api/chat.py` para pasar el `account_id` del `request` a la herramienta.
---
## 12-08-2025 Corrección de `AttributeError` en `DeepResearchTool`

Descripción general: Se resolvió un `AttributeError` en `DeepResearchTool` al intentar acceder a un método `get` en una instancia de `DuckDuckGoSearchTool`.

- **Punto 1**: Se modificó la clase `DeepResearchTool` en `tools/deep_research_tool.py` para que `llm_instance`, `ddg_search_tool`, y `add_web_to_rag_tool` sean pasados como argumentos directos al constructor, en lugar de ser campos de Pydantic. Esto evita que `BaseTool` intente validarlos de una manera que cause el error.
---
## 12-08-2025 Corrección de `SyntaxError` en `DeepResearchTool`

Descripción general: Se resolvió un `SyntaxError` en `DeepResearchTool` debido a una cadena de texto no terminada.

- **Punto 1**: Se añadió la comilla de cierre faltante en la f-string en la línea 67 de `tools/deep_research_tool.py`.
---
## 12-08-2025 Depuración de `ImportError` en `DeepResearchTool`

Descripción general: Se añadió la impresión del traceback completo para depurar un `ImportError` al importar `DeepResearcher` en `tools/deep_research_tool.py`.

- **Punto 1**: Se importó el módulo `traceback` en `tools/deep_research_tool.py`.
- **Punto 2**: Se añadió `traceback.print_exc()` dentro del bloque `except ImportError as e:` para obtener más detalles sobre la causa del error de importación.