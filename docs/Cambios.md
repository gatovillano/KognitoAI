## 08-10-25 Mejora de Herramientas de Tabla en Tiptap Editor
Se han añadido nuevas funcionalidades para la manipulación de tablas en el editor Tiptap, permitiendo a los usuarios gestionar filas y columnas de manera más eficiente.

- **Punto 1**: Se han incorporado botones en la barra de herramientas de Tiptap para añadir filas antes y después de la selección actual.
- **Punto 2**: Se ha añadido un botón para eliminar la fila seleccionada.
- **Punto 3**: Se han incluido botones para añadir columnas antes y después de la selección actual.
- **Punto 4**: Se ha añadido un botón para eliminar la columna seleccionada.
- **Punto 5**: Se ha implementado un botón para eliminar la tabla completa.
- **Punto 6**: La visibilidad de estos nuevos botones está condicionada a que el cursor se encuentre dentro de una tabla, optimizando la interfaz de usuario.

---

## 08-10-25 Actualización de Iconos en la Barra de Herramientas de Tiptap
Se han reemplazado los textos de los botones de las operaciones de tabla por iconos de `lucide-react` en la barra de herramientas del editor Tiptap para una interfaz más visual y limpia.

- **Punto 1**: Los botones para añadir/borrar filas y columnas, y borrar tabla, ahora utilizan iconos (`ArrowUp`, `ArrowDown`, `Minus`, `ArrowLeft`, `ArrowRight`, `Trash2`) en lugar de texto.
- **Punto 2**: Se han añadido las importaciones necesarias para los nuevos iconos en `src/components/TiptapToolbar.tsx`.

---

## 08-10-25 Refinamiento de Iconos de Tabla y Adición de Tooltips en Tiptap Editor
Se han refinado los iconos utilizados para las operaciones de tabla en la barra de herramientas del editor Tiptap, optando por iconos más descriptivos de `lucide-react`. Además, se han añadido tooltips a cada botón para proporcionar una descripción clara de su función al usuario.

- **Punto 1**: Los iconos genéricos para añadir/borrar filas y columnas han sido reemplazados por `Rows3` y `Columns3` respectivamente, y `MinusSquare` para borrar.
- **Punto 2**: Se han implementado `Tooltip`s para cada botón de operación de tabla, mostrando una descripción textual de la acción al pasar el ratón por encima.
- **Punto 3**: Se han añadido las importaciones de `Rows3`, `Columns3`, `MinusSquare`, `Tooltip`, `TooltipContent`, `TooltipProvider`, y `TooltipTrigger` en `src/components/TiptapToolbar.tsx`.

---

## 08-10-25 Corrección: Actualización de Títulos de Eventos
Se ha corregido un problema que impedía la actualización de los títulos de los eventos en la API.

- **Punto 1**: Se añadió el campo `summary: Optional[str] = None` a la clase `EventUpdateRequest` en `api/agenda.py`.
- **Punto 2**: Esta modificación permite que la API reciba y procese correctamente las actualizaciones del título del evento, asegurando que los cambios se reflejen en la base de datos.

---

## 08-10-25 Corrección: TypeError en check_workspace_permission
Se ha corregido el `TypeError` que ocurría al llamar a la función `check_workspace_permission` sin el argumento `required_roles` en varios puntos de la API.

- **Punto 1**: Se añadió el argumento `required_roles` a todas las llamadas de `check_workspace_permission` en `core/notes_manager.py`, especificando los roles adecuados para cada operación (visualización, actualización, eliminación, vinculación/desvinculación de perfiles).
- **Punto 2**: Se añadió el argumento `required_roles` a todas las llamadas de `check_workspace_permission` en `api/notes.py`, especificando los roles adecuados para cada operación (visualización, actualización, eliminación, vinculación/desvinculación de perfiles).

---

## 08-10-25 Corrección: Endpoint de Vinculación de Perfiles en Álbumes
Se ha corregido el endpoint de vinculación y desvinculación de perfiles en álbumes para que el `profile_id` se envíe en el cuerpo de la solicitud en lugar de como parámetro de ruta, resolviendo el error `404 Not Found`.

- **Punto 1**: Se definió el modelo Pydantic `ProfileLinkRequest` en `api/galleries.py` para manejar el `profile_id` en el cuerpo de la solicitud.
- **Punto 2**: Se modificaron los decoradores `@router.post` de `link_profile_to_album` y `unlink_profile_from_album` en `api/galleries.py` para eliminar el `profile_id` de la ruta.
- **Punto 3**: Se actualizaron las firmas de las funciones `link_profile_to_album` y `unlink_profile_from_album` para aceptar `profile_link_request: ProfileLinkRequest`.
- **Punto 4**: Se ajustó la lógica interna de ambas funciones para utilizar `profile_link_request.profile_id`.