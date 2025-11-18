## 18-11-2025 Actualización de alineación de botones de citación

### Descripción general:
Se solicitó corregir la alineación vertical de los botones de citación en el chat y asegurar la consistencia del tamaño de fuente. La solución implicó modificar `MarkdownRenderer` para envolver el texto y `SourceButton` en un contenedor `inline-flex` con `align-items: baseline;`, y ajustar las clases de `SourceButton` en `ChatMessage.tsx`.

- **Modificación en MarkdownRenderer.tsx**: Se envolvió la salida de `marked.parseInline` y `SourceButton` en un `<span>` con las clases `inline-flex` y `items-baseline` para mejorar la alineación vertical de los elementos en línea.
- **Modificación en ChatMessage.tsx**: Se eliminaron las clases de alineación redundantes (`align-middle`, `align-text-bottom`) y se aseguró que `SourceButton` tuviera la clase `text-xl` para coincidir con el tamaño de fuente. Se verificó que estos cambios ya estaban aplicados en el archivo.
---
## 18-11-2025 Corrección de Indentación en cognee_integration.py

### Descripción general:
Se identificó y corrigió un `IndentationError` en el archivo `knowledge_graph/cognee_integration.py` en la línea 1272. Este error impedía la correcta ejecución del módulo.

- **Punto 1**: Se ajustó la indentación de los bucles `for node in path_object.nodes:` y `for rel in path_object.relationships:` dentro del método `_format_advanced_search_results` para asegurar la correcta anidación y sintaxis de Python.
---
## 18-11-2025 Reubicación del Acceso al Módulo de Análisis

### Descripción general:
Se modificó la página de Colecciones de Conocimientos (`rag/page.tsx`) para reubicar el acceso al módulo de Análisis. Anteriormente, se accedía a través de un `DropdownMenu` global, pero ahora se ha implementado un botón dedicado de "Análisis" junto al botón "Subir Documento" en la parte superior derecha de la página.

- **Punto 1**: Se añadió un nuevo botón con el texto "Análisis" y el icono `ScanSearch` al lado del botón "Subir Documento".
- **Punto 2**: El nuevo botón de "Análisis" tiene un estilo idéntico al botón "Subir Documento" (azul, mismo tamaño, etc.).
- **Punto 3**: Se configuró el `onClick` del botón de "Análisis" para navegar a la ruta `/analysis`, proporcionando un acceso directo y visible al módulo de análisis global.
---
## 18-11-2025 Actualización de Icono y Estilo del Botón de Análisis

### Descripción general:
Se actualizó el botón de "Análisis" en la página de Colecciones de Conocimientos (`rag/page.tsx`) para que su icono y estilo coincidan con las convenciones del proyecto.

- **Punto 1**: Se cambió el icono del botón de "Análisis" de `ScanSearch` a `BarChart3` para alinearse con el icono utilizado en el `Sidebar.tsx` para la sección de "Análisis".
- **Punto 2**: Se ajustaron las clases CSS del botón de "Análisis" para que su color y apariencia sean idénticos a los del botón "Subir Documento", utilizando `bg-primary hover:bg-primary/90`.
---
## 18-11-2025 Corrección de Importación de Icono en rag/page.tsx

### Descripción general:
Se corrigió un `ReferenceError` (`BarChart3 is not defined`) en `src/app/(dashboard)/rag/page.tsx` añadiendo la importación faltante del componente `BarChart3` de `lucide-react`.

- **Punto 1**: Se añadió `BarChart3` a la lista de importaciones de `lucide-react` en la parte superior del archivo `rag/page.tsx`.
---
## 18-11-2025 Eliminación del Acceso al Módulo de Análisis del Sidebar

### Descripción general:
Se eliminó el enlace directo al módulo de "Análisis" del `Sidebar.tsx`, ya que ahora se accede a esta funcionalidad a través de un botón dedicado en la página de Colecciones de Conocimientos (`rag/page.tsx`).

- **Punto 1**: Se eliminó el componente `Link` y su `Button` asociado que dirigían a la ruta `/analysis` del `Sidebar.tsx`.
---
## 18-11-2025 Configuración de Faster Whisper para GPU con Fallback a CPU

### Descripción general:
Se modificó `utils/audio_transcriber.py` para mejorar la robustez en la carga del modelo Faster Whisper, permitiendo el uso de GPU (`cuda`) si está disponible y configurado correctamente, con un fallback automático a CPU en caso de fallo o indisponibilidad de la GPU.

- **Punto 1**: Se añadió la importación de `torch` para verificar dinámicamente la disponibilidad de CUDA (`torch.cuda.is_available()`).
- **Punto 2**: La función `load_whisper_model` ahora determina el dispositivo (`cuda` o `cpu`) y el `compute_type` (`int8` para GPU, `float32` para CPU) de forma dinámica.
- **Punto 3**: Se implementó un bloque `try-except` para intentar cargar el modelo en el dispositivo determinado y, si falla en GPU, se realiza un segundo intento en CPU con `compute_type="float32"`.
- **Punto 4**: La función `get_whisper_model` ahora utiliza `asyncio.get_running_loop().run_in_executor(None, load_whisper_model)` para ejecutar la carga del modelo en un hilo separado, evitando bloquear el event loop principal de la aplicación asíncrona.
