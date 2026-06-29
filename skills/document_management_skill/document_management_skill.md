# Document Management Skill

Herramienta para generar PDFs de calidad profesional.

## Reglas de diseño A4 (obligatorias)

- Tamaño de página: **A4** (210mm x 297mm / 21cm x 29.7cm)
- Márgenes: **2cm** en todos los bordes
- Ancho útil máximo: **17cm** (21cm - 2cm izquierda - 2cm derecha)
- Alto útil máximo por página: **25.7cm** (29.7cm - 2cm superior - 2cm inferior)

## Uso del `create_pdf_tool`

- Enviar SIEMPRE `is_html=True`
- Envolver el contenido principal en `<div class="content">`
- Usar `<div class="cover">` solo para la portada de la primera página
- No usar anchos/altos fijos mayores a 17cm x 25cm
- Las imágenes y tablas deben usar `max-width: 100%`

## Componentes CSS disponibles

| Clase | Uso |
|-------|-----|
| `.cover` | Portada (ocupa exactamente la primera página A4) |
| `.content` | Contenedor principal del cuerpo del documento |
| `.card` | Sección resaltada |
| `.info-box` / `.warning-box` / `.error-box` | Notas y advertencias |
| `.grid-2` | Diseño de dos columnas |
