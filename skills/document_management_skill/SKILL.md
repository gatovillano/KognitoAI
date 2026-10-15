---
name: document-management
description: Use when creating, editing, updating metadata, or generating professional
  PDF documents.
---

# Document Management Skill

Gestión de documentos de la **Base de Conocimiento RAG** y generación de PDFs de calidad profesional.

> ⚠️ **DIFERENCIACIÓN IMPORTANTE DE HERRAMIENTAS:**
> - `get_document_content_tool`: Lee documentos indexados en la **Base de Conocimiento RAG** (usando `file_name`). NO USAR para OnlyOffice.
> - `get_document_list_tool`: Lista documentos de la **Base de Conocimiento RAG**. NO USAR para OnlyOffice.
> - `create_pdf_tool`: Genera PDFs profesionales descargables.
> - Para editar o leer documentos ofimáticos editables (Word .docx, Excel .xlsx, PPT .pptx), usa **`onlyoffice_skill`** (`read_onlyoffice_document`, `edit_onlyoffice_document`, `create_onlyoffice_document`).

Los documentos PDF generados con esta herramienta se guardan automáticamente en la nube de Documentos (OnlyOffice) dentro de una carpeta dedicada y identificada visualmente: **`🤖 Documentos PDF (Agente)`**.

## Parámetros de Diseño Dinámico

Al usar `create_pdf_tool`, puedes configurar la apariencia de la página usando los siguientes parámetros opcionales:

* `orientation`: `"portrait"` (vertical, por defecto) o `"landscape"` (horizontal).
* `margin`: Margen exterior de la página, por defecto `"2cm"`.
* `theme`: Tema estético integrado (`"modern"`, `"emerald"`, `"amber"`, `"minimalist"`).
* `custom_css`: Hoja de estilos CSS opcional inyectada al final.
* `header_text` / `footer_text`: Personalizan el encabezado superior derecho y el pie de página inferior izquierdo. Puedes usar los placeholders `[page]` y `[pages]` (ej. `"Reporte - Pág. [page] de [pages]"`).

## Reglas de diseño A4 (obligatorias)

* Tamaño de página: **A4** (210mm x 297mm / 21cm x 29.7cm)
* El ancho útil máximo en orientación Vertical es **17cm** (21cm - 2cm izquierda - 2cm derecha).
* Envolventes: El contenido principal del cuerpo del documento debe ir en `<div class="content">`.
* Recursos locales: Se pueden utilizar imágenes y fuentes del espacio de trabajo mediante rutas relativas directamente en el HTML (ej. `<img src="media/logo.png">`).

## Componentes CSS Premium Disponibles

| Clase | Descripción |
|---|---|
| `.cover-classic` | Portada clásica centrada, fondo azul oscuro de página completa sin márgenes. |
| `.cover-modern` | Portada moderna con degradado oscuro de fondo y un pie de metadatos delimitado. |
| `.cover-minimal` | Portada elegante de fondo claro con tipografía masiva asimétrica. |
| `.content` | Contenedor principal para el cuerpo del texto. |
| `.card` | Tarjeta con fondo claro y bordes suaves. |
| `.card-accent` | Tarjeta con borde izquierdo destacado del color del tema activo. |
| `.info-box` / `.success-box` / `.warning-box` / `.error-box` / `.note-box` | Cajas de notas y estados. |
| `.grid-2` / `.grid-3` / `.grid-4` | Diseños de columnas flexibles adaptativos con protección de saltos de página. |
| `.badge` | Etiquetas pequeñas. Subclases: `.badge-primary`, `.badge-success`, `.badge-warning`, `.badge-error`. |
| `.table-striped` | Filas alternas con sombreado zebra. |
| `.table-bordered` | Bordes completos y definidos en celdas de tabla. |
| `.table-dense` | Espaciado interno compacto para tablas extensas. |
| `.page-break` | Fuerza un salto de página inmediato antes del elemento. |
| `.no-break` | Evita que WeasyPrint corte la página en medio del elemento. |
