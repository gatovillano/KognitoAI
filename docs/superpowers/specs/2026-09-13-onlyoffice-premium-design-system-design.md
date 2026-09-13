# Sistema de Diseño Premium para Documentos OnlyOffice (Word, Excel, PowerPoint)

## 1. Contexto y Objetivos

Actualmente, el módulo OnlyOffice de la plataforma KAI permite crear y editar archivos básicos de Word (`.docx`) y Excel (`.xlsx`), mientras que PowerPoint (`.pptx`) solo permite la creación de un archivo vacío sin soporte de edición. Además, los archivos se inicializan completamente vacíos, sin portadas, sin estructura visual predeterminada y con opciones de diseño limitadas a tablas básicas y formateo Markdown elemental.

El objetivo de esta mejora es dotar al agente de un **Sistema de Diseño Premium Unificado y Modular** que le permita:
1. Generar documentos con un acabado corporativo y editorial de alto nivel en Word, Excel y PowerPoint.
2. Contar con un catálogo de **Plantillas Maestras** preconfiguradas (*Reporte Ejecutivo*, *Propuesta Comercial*, *Dashboard Financiero*, *Pitch Deck*, etc.) que generan esqueletos completos en un solo paso.
3. Disponer de **Componentes Modulares** reutilizables (Portadas ejecutivas, Cajas callout de alerta en Markdown, Tarjetas de métricas/KPI, Gráficos nativos de Office, y Diapositivas temáticas por diseño).
4. Mantener una identidad visual coherente y consistente entre los 3 tipos de documentos gracias a un sistema central de temas y paletas tipográficas y de color.
5. Operar de forma híbrida: estética inteligente y profesional por defecto, respetando estrictamente personalizaciones cuando el usuario las solicite.

---

## 2. Arquitectura del Sistema

Se adopta un **Enfoque Modular Desacoplado** creando el paquete `skills/onlyoffice_skill/design/` para no sobrecargar los scripts existentes de las tools y facilitar el mantenimiento y las pruebas unitarias:

```
skills/onlyoffice_skill/
├── SKILL.md                                  # Documentación y prompts actualizados para el agente
├── design/                                   # NUEVO: Paquete de diseño premium
│   ├── __init__.py
│   ├── themes.py                             # Paletas de color, tipografías y tokens de diseño
│   ├── docx_engine.py                        # Portadas, callouts, KPI cards, numeración de páginas
│   ├── xlsx_engine.py                        # KPI cards, gráficos nativos openpyxl, formato condicional
│   ├── pptx_engine.py                        # Creación y layouts de diapositivas (Title, Agenda, Cards, KPIs)
│   └── template_registry.py                  # Catálogo de plantillas maestras completas
└── scripts/
    ├── create_onlyoffice_document_tool.py    # Ampliado con template, theme, title, subtitle
    ├── edit_onlyoffice_document_tool.py      # Ampliado con nuevas acciones modulares y soporte PPTX
    ├── list_onlyoffice_documents_tool.py
    ├── read_onlyoffice_document_tool.py
    └── search_onlyoffice_documents_tool.py
```

---

## 3. Especificación de Componentes

### 3.1. Sistema Central de Temas (`themes.py`)

Define los tokens visuales para cada tema, accesibles desde los tres motores:

```python
THEMES = {
    "corporate_blue": {
        "name": "Corporate Blue",
        "primary": "1E3A8A",       # Azul Marino Profundo
        "secondary": "2563EB",     # Azul Real
        "accent": "3B82F6",        # Azul Claro
        "bg_light": "F8FAFC",      # Pizarra Suave
        "bg_tint": "EFF6FF",       # Tint azul pastel
        "border": "CBD5E1",        # Gris borde sutil
        "text_primary": "1E293B",  # Texto oscuro principal
        "text_muted": "64748B",    # Texto secundario
        "font_heading": "Segoe UI",
        "font_body": "Segoe UI",
    },
    "emerald_green": { ... },      # Verde bosque / Esmeralda
    "dark_slate": { ... },         # Carbón / Gris frío
    "sunset_amber": { ... },       # Ámbar oscuro / Naranja cálido
    "violet_gold": { ... },        # Púrpura real / Índigo
    "minimalist_gray": { ... },     # Negro carbón / Gris neutro
}
```

- Función `get_theme(theme_name: str) -> dict`: Retorna el tema solicitado con fallback a `corporate_blue`.
- Soporte de overrides dinámicos (color primario, tipografía) manteniendo la armonía de contrastes.

---

### 3.2. Motor Word (`docx_engine.py`)

1. **Portadas Ejecutivas (`add_cover_page`)**:
   - Estilos:
     - `modern`: Banda superior/lateral con color primario, título (30pt bold), subtítulo (14pt), tabla de metadatos (Autor, Organización, Fecha, Versión) y salto de página/sección sin encabezados en la portada.
     - `minimal`: Espaciado generoso, título limpio, línea de acento horizontal delgada (1pt) y metadatos sutiles al pie.
     - `header_block`: Bloque sólido superior a todo el ancho con título en texto blanco contrastado.
2. **Cajas de Alerta y Callouts (`render_callout`)**:
   - Integrado en el parser Markdown para detectar:
     - `> [!NOTE] texto`: Fondo azul pastel, barra izquierda `#2563EB` (3pt), etiqueta `ℹ️ NOTA`.
     - `> [!TIP] texto`: Fondo menta pastel, barra izquierda `#059669` (3pt), etiqueta `💡 CONSEJO`.
     - `> [!WARNING] texto`: Fondo ámbar pastel, barra izquierda `#D97706` (3pt), etiqueta `⚠️ ADVERTENCIA`.
     - `> [!IMPORTANT]` / `> [!CAUTION]`: Fondo coral pastel, barra izquierda `#DC2626` (3pt), etiqueta `🚨 IMPORTANTE`.
     - Citas generales (`> texto`): Fondo gris claro suave con barra lateral gris pizarra.
3. **Tarjetas Métricas / KPI Cards (`add_kpi_cards`)**:
   - Inserta una cuadrícula de 2 a 4 tarjetas en una tabla sin bordes exteriores.
   - Cada celda tiene fondo `bg_light`, borde sutil, valor métrico destacado (18-22pt bold color primario) y etiqueta descriptiva (9-10pt).
4. **Encabezados y Pies de Página Dinámicos**:
   - Inserción de campos XML nativos `PAGE` y `NUMPAGES` (*"Página X de Y"*), con nombre de documento alineado a la izquierda.

---

### 3.3. Motor Excel (`xlsx_engine.py`)

1. **Panel Superior de KPI Cards (`add_kpi_cards`)**:
   - Crea tarjetas combinando celdas en las filas superiores (ej: A2:B4, D2:E4, G2:H4).
   - Fondo `bg_light`, borde temático, etiqueta en mayúsculas pequeñas, valor en fuente grande (18pt bold) e indicador de tendencia opcional (*▲ +12%* en verde o *▼ -5%* en rojo).
2. **Gráficos Nativos Office (`add_chart`)**:
   - Usa `openpyxl.chart` (`BarChart`, `LineChart`, `PieChart`).
   - Parámetros: tipo de gráfico, celda de anclaje (ej. `F8`), rango de datos, rango de categorías, título, ancho y alto.
   - Se aplican los colores del tema a las series de datos del gráfico.
3. **Formato Condicional Inteligente (`apply_conditional_formatting`)**:
   - `color_scale`: Escalas de color (gradientes de verde a rojo para métricas o azul a blanco).
   - `status_highlights`: Resaltado automático para celdas de estado (`Completado` en verde, `En Progreso` en amarillo, `Atrasado` en rojo).
4. **Optimización de Cuadrícula**:
   - Ajuste automático de ancho de columnas para evitar `#REF!` o `###`.
   - Congelamiento de paneles automático bajo la fila de encabezados.

---

### 3.4. Motor PowerPoint (`pptx_engine.py`)

1. **Gestión de Diapositivas (`add_slide`) con Diseños Temáticos**:
   - **`title`**: Portada con fondo sólido temático (o claro con acentos), título principal (36-40pt bold), subtítulo (18pt), autor y fecha.
   - **`agenda`**: Título con barra de acento inferior y lista estructurada en tarjetas rectangulares numeradas.
   - **`content`**: Encabezado superior con barra de color, y caja de contenido con viñetas espaciadas profesionalmente.
   - **`two_columns` / `three_columns`**: Tarjetas paralelas lado a lado con fondo suave, borde fino, subtítulo de tarjeta y contenido en viñetas.
   - **`kpi_metrics`**: 3 o 4 tarjetas de estadísticas con números gigantes (40-44pt bold color primario), etiquetas y subtítulo.
   - **`conclusion`**: Diapositiva de cierre con llamada a la acción, viñetas de conclusiones y datos de contacto.
2. **Tablas en Diapositivas (`add_table`)**:
   - Tabla estilizada con cabecera en color primario, texto blanco y filas alternas legibles.
3. **Notas del Orador (`speaker_notes`)**:
   - Asignación de notas en cada diapositiva para soporte al presentador.

---

### 3.5. Catálogo de Plantillas Maestras (`template_registry.py`)

| Tipo | ID Plantilla | Descripción y Contenido Inicial |
|---|---|---|
| **Word** | `executive_report` | Portada moderna, Resumen Ejecutivo con 3 KPI cards, Secciones de Contexto, Hallazgos (con tabla formateada), Conclusiones y pie con número de página. |
| **Word** | `commercial_proposal` | Portada elegante, Sobre Nosotros, Alcance de Trabajo, Cronograma, Tabla de Cotización con totales y Condiciones de Contratación. |
| **Word** | `project_charter` | Portada minimalista, Objetivos, Alcance, Matriz de Riesgos y Tabla de Hitos. |
| **Excel** | `financial_budget` | Hoja *"Resumen"* con 3 KPI cards superiores (Ingresos, Gastos, Margen) y gráfico de columnas; hojas *"Ingresos"* y *"Gastos"* con tablas y fórmulas de totales. |
| **Excel** | `sales_dashboard` | Panel de ventas con KPI cards, tabla con formato condicional de cumplimiento y gráfico de barras/torta. |
| **Excel** | `project_tracker` | Planilla de tareas con responsables, fechas, estados formateados condicionalmente y barra/fórmulas de avance. |
| **PowerPoint** | `pitch_deck` | 6 diapositivas completas: Portada, Problema, Solución, Tracción/Métricas (KPI cards), Modelo de Negocio y Cierre/Equipo. |
| **PowerPoint** | `quarterly_review` | 5 diapositivas ejecutivas: Portada QBR, Resumen de Rendimiento, KPIs Clave, Proyectos Estratégicos y Próximos Pasos. |

---

### 3.6. Interfaz y Ampliación de Tools

#### `create_onlyoffice_document_tool.py`:
- Parámetros adicionales:
  - `template: Optional[str]`: ID de plantilla (ej. `'executive_report'`, `'financial_budget'`, `'pitch_deck'`).
  - `theme: Optional[str]`: Tema visual (ej. `'corporate_blue'`, `'emerald_green'`, `'dark_slate'`, etc.).
  - `title: Optional[str]`: Título del documento.
  - `subtitle: Optional[str]`: Subtítulo o nombre de organización.
- Si se proporciona `template`, se delega en `template_registry.create_from_template(...)`. Si no, se crea el archivo base aplicando los estilos iniciales del tema elegido.

#### `edit_onlyoffice_document_tool.py`:
- Nuevas acciones en `SUPPORTED_ACTIONS`:
  - DOCX: `docx_add_cover_page`, `docx_add_kpi_cards`.
  - XLSX: `xlsx_add_kpi_cards`, `xlsx_add_chart`, `xlsx_apply_conditional_formatting`.
  - PPTX: `pptx_add_slide`, `pptx_add_table`.
- Mejora del parser Markdown para soportar bloques `> [!NOTE]`, `> [!TIP]`, `> [!WARNING]`, etc.

---

## 4. Plan de Pruebas y Verificación

1. **Pruebas Unitarias Aisladas (`tests/test_onlyoffice_design_system.py`)**:
   - Verificación de carga y paletas de `themes.py`.
   - Generación y validación de XML/elementos en Word (`add_cover_page`, `add_kpi_cards`, callouts).
   - Generación y validación de hojas Excel (`add_kpi_cards`, `add_chart`, formato condicional).
   - Generación y validación de presentaciones PPTX (`add_slide` para cada tipo de layout).
   - Instanciación de cada plantilla del catálogo (`template_registry`).
2. **Pruebas de Integración de Tools**:
   - Creación de documentos usando `create_onlyoffice_document` con y sin plantilla.
   - Modificación modular usando `edit_onlyoffice_document` con las nuevas acciones.
3. **Verificación Visual de Documentos**:
   - Comprobación de que los archivos generados abren sin errores de corrupción en OnlyOffice y suites ofimáticas compatibles.
