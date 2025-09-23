## 23-09-2025 Implementación de botón para invertir el orden de las fotos en la galería
Se ha añadido un botón en la vista de detalle de la galería para permitir a los usuarios invertir el orden de las fotos mostradas. Esto facilita la organización y visualización de las imágenes según sus preferencias.

- **Función `handleInvertOrder`**: Se creó una nueva función en `src/app/(dashboard)/galleries/[albumId]/client.tsx` que invierte el orden de las fotos en el estado local del álbum y actualiza la propiedad `order` de cada foto.
- **Botón "Invertir Orden"**: Se añadió un botón en la interfaz de usuario de `src/app/(dashboard)/galleries/[albumId]/client.tsx` que, al ser presionado, ejecuta la función `handleInvertOrder`.
- **Actualización de orden**: La función `handleInvertOrder` actualiza la propiedad `order` de las fotos en el frontend, y se espera que el usuario haga clic en el botón "Guardar Orden" para persistir estos cambios en el backend.

---

## 23-09-2025 Integración de Lightbox en la vista de detalle de la galería
Se ha integrado el componente `yet-another-react-lightbox` en la vista de detalle de la galería para mejorar la experiencia de visualización de imágenes.

- **Importación de Lightbox**: Se importaron `Lightbox` y sus estilos en `src/app/(dashboard)/galleries/[albumId]/client.tsx`.
- **Estados de Lightbox**: Se añadieron los estados `lightboxOpen` y `lightboxIndex` en `AlbumDetailPageClient` para controlar la visibilidad y la imagen actual del lightbox.
- **Actualización de `PhotoResponse`**: Se modificó la interfaz `PhotoResponse` en `src/types/gallery.ts` para incluir la propiedad `order: number;` para el correcto funcionamiento del reordenamiento.
- **Activación del Lightbox**: Se modificó el `onClick` del componente `PhotoCard` en `src/app/(dashboard)/galleries/[albumId]/client.tsx` para que, al hacer clic en una imagen, se abra el nuevo lightbox en lugar del visor de imágenes anterior.
- **Eliminación de visor antiguo**: Se eliminó el componente de visor de imágenes personalizado que existía previamente en `src/app/(dashboard)/galleries/[albumId]/client.tsx` para evitar duplicidad y usar la funcionalidad completa del nuevo lightbox.

---

## 23-09-2025 Guardado automático al invertir el orden de las fotos
Se modificó la función `handleInvertOrder` para que, al invertir el orden de las fotos, los cambios se guarden automáticamente en el backend.

- **Llamada a `handleSaveOrder`**: La función `handleInvertOrder` ahora llama a `handleSaveOrder` después de actualizar el orden de las fotos en el estado local, asegurando la persistencia de los cambios.