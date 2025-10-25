## 25-10-24 Visualización de adjuntos en CommonChat.tsx
Descripción general: Se solucionó un problema donde los adjuntos (imágenes y contexto RAG) no se visualizaban correctamente en los mensajes del usuario en el componente CommonChat.tsx.

- **Inconsistencia de propiedad de imagen**: Se cambió el nombre de la propiedad `image_base64` a `image` en la interfaz `ChatMessageType` para que coincidiera con la propiedad esperada por el componente `ChatMessage`.
- **Paso de `ragContext`**: Se modificó la función `handleSendMessage` para asegurar que el `ragContext` (archivos adjuntos) se incluya en el objeto `userMessage` que se muestra en el frontend.
---
## 25-10-24 Visualización de adjuntos desde ContextSelectorButton
Descripción general: Se corrigió la falta de visualización de los adjuntos seleccionados a través del `ContextSelectorButton` en los mensajes del usuario.

- **Actualización de la prop `onContextSelected`**: Se modificó la prop `onContextSelected` del `ContextSelectorButton` en `src/components/CommonChat.tsx` para que apunte a la función `setSelectedContext`, permitiendo que los elementos seleccionados se pasen correctamente al estado y se visualicen.