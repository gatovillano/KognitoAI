# Mejoras de Diseño HTML/CSS en CreatePDFTool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mejorar la herramienta `CreatePDFTool` corrigiendo errores de sintaxis CSS, añadiendo soporte para recursos locales, inyección de CSS personalizado, temas y control dinámico del diseño de página desde la firma del tool.

**Architecture:** Añadir parámetros a `CreatePDFInput`, configurar `base_url=os.getcwd()` en WeasyPrint, generar dinámicamente la regla `@page` basada en los parámetros y enriquecer el CSS predefinido con componentes premium.

**Tech Stack:** Python, WeasyPrint, Markdown, Pytest

## Global Constraints

- El tamaño de página es estrictamente A4 (21cm x 29.7cm).
- Todos los nuevos parámetros deben ser opcionales y con valores por defecto para no romper la compatibilidad con llamadas existentes.
- Los comandos de prueba se deben ejecutar utilizando el entorno `venv_host` y con `PYTHONPATH=.`.

---

### Task 1: Setup Tests and Input Schema Changes

**Files:**
- Create: `tests/test_create_pdf_tool.py`
- Modify: `skills/document_management_skill/scripts/create_pdf_tool.py:25-48`
- Modify: `skills/document_management_skill/scripts/create_pdf_tool.py:400-410`

**Interfaces:**
- Consumes: `skills.document_management_skill.scripts.create_pdf_tool.CreatePDFInput`
- Produces: `CreatePDFInput` con campos adicionales (`custom_css`, `orientation`, `margin`, `theme`, `header_text`, `footer_text`).

- [ ] **Step 1: Write the failing test**

  Crear el archivo `tests/test_create_pdf_tool.py` con el siguiente test inicial:
  
  ```python
  import pytest
  from skills.document_management_skill.scripts.create_pdf_tool import CreatePDFInput, CreatePDFTool

  def test_pdf_input_schema_has_new_parameters():
      # Verify that we can instantiate CreatePDFInput with all new parameters
      input_data = CreatePDFInput(
          content="test content",
          custom_css="body { color: red; }",
          orientation="landscape",
          margin="1.5cm",
          theme="emerald",
          header_text="Custom Header",
          footer_text="Custom Footer"
      )
      assert input_data.custom_css == "body { color: red; }"
      assert input_data.orientation == "landscape"
      assert input_data.margin == "1.5cm"
      assert input_data.theme == "emerald"
      assert input_data.header_text == "Custom Header"
      assert input_data.footer_text == "Custom Footer"
  ```

- [ ] **Step 2: Run test to verify it fails**

  Ejecutar:
  ```bash
  PYTHONPATH=. venv_host/bin/pytest tests/test_create_pdf_tool.py::test_pdf_input_schema_has_new_parameters -v
  ```
  Expected: FAIL con error de validación (Pydantic ValidationError indicando que los campos extra no están permitidos o no existen).

- [ ] **Step 3: Write minimal implementation**

  Modificar `skills/document_management_skill/scripts/create_pdf_tool.py` para añadir los campos al esquema `CreatePDFInput`:
  
  ```python
  class CreatePDFInput(BaseModel):
      content: str = Field(
          ...,
          description=(
              "El contenido a convertir. DEBE ser un texto largo y estructurado. PREFERIBLEMENTE HTML. "
              "EL TAMAÑO DE PÁGINA ES ESTRICTAMENTE A4 (21cm x 29.7cm). Diseña tu HTML para que encaje en este formato: "
              "el ancho imprimible es de ~17cm (debido a márgenes de 2cm) y el alto de ~25.7cm por página. "
              "Usa clases estructuradas y evita desbordar estas dimensiones."
          )
      )
      is_html: bool = Field(
          True,
          description="DEBE ser True si envías HTML. Se recomienda encarecidamente usar HTML para evitar bloques de texto sin formato."
      )
      filename: Optional[str] = Field(
          None,
          description="Optional filename for the generated PDF. If not provided, a random name will be used."
      )
      title: Optional[str] = Field(
          "Documento Generado",
          description="The title of the document, used in the header."
      )
      custom_css: Optional[str] = Field(
          None,
          description="CSS adicional que se inyectará al final para personalizar o sobrescribir el estilo."
      )
      orientation: Optional[str] = Field(
          "portrait",
          description="Orientación de la página: 'portrait' (vertical) o 'landscape' (horizontal)."
      )
      margin: Optional[str] = Field(
          "2cm",
          description="Margen exterior de las páginas (ej. '2cm', '1.5in', '20mm')."
      )
      theme: Optional[str] = Field(
          "modern",
          description="Tema de color predefinido: 'modern', 'emerald', 'amber', 'minimalist'."
      )
      header_text: Optional[str] = Field(
          None,
          description="Texto opcional para la cabecera superior derecha. Soporta placeholders [page] y [pages]."
      )
      footer_text: Optional[str] = Field(
          None,
          description="Texto opcional para el pie de página inferior izquierdo. Soporta placeholders [page] y [pages]."
      )
  ```
  
  Y también actualizar la firma del método `_arun` en `CreatePDFTool`:
  
  ```python
      async def _arun(
          self, 
          content: str, 
          is_html: bool = False, 
          filename: Optional[str] = None, 
          title: str = "Documento Generado",
          custom_css: Optional[str] = None,
          orientation: str = "portrait",
          margin: str = "2cm",
          theme: str = "modern",
          header_text: Optional[str] = None,
          footer_text: Optional[str] = None,
          **kwargs: Any
      ) -> Any:
  ```

- [ ] **Step 4: Run test to verify it passes**

  Ejecutar:
  ```bash
  PYTHONPATH=. venv_host/bin/pytest tests/test_create_pdf_tool.py::test_pdf_input_schema_has_new_parameters -v
  ```
  Expected: PASS

- [ ] **Step 5: Commit**

  ```bash
  git add tests/test_create_pdf_tool.py skills/document_management_skill/scripts/create_pdf_tool.py
  git commit -m "test & feat: add new parameters to CreatePDFInput and CreatePDFTool._arun"
  ```

---

### Task 2: Dynamic Page Customization & base_url support

**Files:**
- Modify: `skills/document_management_skill/scripts/create_pdf_tool.py` (métodos `_get_modern_css` y `_arun`)
- Modify: `tests/test_create_pdf_tool.py` (añadir tests)

**Interfaces:**
- Consumes: Parámetros del tool (`custom_css`, `orientation`, `margin`, `theme`, `header_text`, `footer_text`).
- Produces: CSS `@page` generado dinámicamente, inyección de CSS personalizado y resolución de recursos locales configurando `base_url`.

- [ ] **Step 1: Write the failing test**

  Añadir el siguiente test a `tests/test_create_pdf_tool.py`:
  
  ```python
  import os
  from unittest.mock import patch, MagicMock
  
  @pytest.mark.asyncio
  async def test_pdf_generation_with_custom_options():
      tool = CreatePDFTool()
      
      # Mock the WeasyPrint HTML and CSS calls to capture the arguments
      with patch("skills.document_management_skill.scripts.create_pdf_tool.HTML") as mock_html:
          mock_html_inst = MagicMock()
          mock_html.return_value = mock_html_inst
          
          await tool._arun(
              content="<h1>Test Customization</h1>",
              is_html=True,
              title="Custom PDF",
              custom_css="h1 { color: purple; }",
              orientation="landscape",
              margin="3cm",
              theme="emerald",
              header_text="Header Page [page] of [pages]",
              footer_text="Footer Info"
          )
          
          mock_html.assert_called_once()
          call_kwargs = mock_html.call_args[1]
          
          html_string = call_kwargs["string"]
          base_url = call_kwargs["base_url"]
          
          # Assert base_url matches current workspace directory
          assert base_url == os.getcwd()
          
          # Assert CSS variables and rules are injected correctly
          assert "size: A4 landscape;" in html_string
          assert "margin: 3cm;" in html_string
          assert "h1 { color: purple; }" in html_string
          
          # Assert emerald theme colors are active
          assert "--primary: #10b981;" in html_string
          
          # Assert header/footer with counter replacements
          assert 'content: "Header Page " counter(page) " of " counter(pages);' in html_string
          assert 'content: "Footer Info";' in html_string
  ```

- [ ] **Step 2: Run test to verify it fails**

  Ejecutar:
  ```bash
  PYTHONPATH=. venv_host/bin/pytest tests/test_create_pdf_tool.py::test_pdf_generation_with_custom_options -v
  ```
  Expected: FAIL (porque `_arun` no soporta aún estos parámetros en su lógica interna ni define el CSS dinámico).

- [ ] **Step 3: Write minimal implementation**

  1. Implementar la función auxiliar `format_css_string` y actualizar `_get_modern_css` en `skills/document_management_skill/scripts/create_pdf_tool.py`:
  
  ```python
      def _format_css_string(self, text: str) -> str:
          """Format string replacing placeholders with CSS counters."""
          escaped = text.replace('"', '\\"')
          # Split by [page] and [pages] to insert them outside the CSS quotes
          parts = re.split(r'(\[page\]|\[pages\])', escaped)
          formatted_parts = []
          for part in parts:
              if part == '[page]':
                  formatted_parts.append('" counter(page) "')
              elif part == '[pages]':
                  formatted_parts.append('" counter(pages) "')
              elif part:
                  formatted_parts.append(f'"{part}"')
          return " ".join(formatted_parts)

      def _get_modern_css(
          self,
          orientation: str = "portrait",
          margin: str = "2cm",
          theme: str = "modern",
          header_text: Optional[str] = None,
          footer_text: Optional[str] = None
      ) -> str:
          """Returns a high-end professional CSS string for the PDF styling."""
          # Theme mapping
          if theme == "emerald":
              primary = "#10b981"
              primary_light = "#ecfdf5"
              primary_dark = "#047857"
              secondary = "#64748b"
          elif theme == "amber":
              primary = "#f59e0b"
              primary_light = "#fffbeb"
              primary_dark = "#b45309"
              secondary = "#78716c"
          elif theme == "minimalist":
              primary = "#0f172a"
              primary_light = "#f8fafc"
              primary_dark = "#000000"
              secondary = "#475569"
          else:  # modern (default)
              primary = "#2563eb"
              primary_light = "#eff6ff"
              primary_dark = "#1e40af"
              secondary = "#64748b"

          # Headers and footers
          header_val = header_text if header_text is not None else "Página [page] de [pages]"
          footer_val = footer_text if footer_text is not None else "Generado por KAI AI System"

          css_header = self._format_css_string(header_val)
          css_footer = self._format_css_string(footer_val)

          return f"""
          @page {{
              size: A4 {orientation};
              margin: {margin};
              @top-right {{
                  content: {css_header};
                  font-family: 'Inter', sans-serif;
                  font-size: 8pt;
                  color: #a0aec0;
              }}
              @bottom-left {{
                  content: {css_footer};
                  font-family: 'Inter', sans-serif;
                  font-size: 8pt;
                  color: #a0aec0;
              }}
          }}

          /* Página sin márgenes para fondos completos */
          @page :first {{
              margin: 0;
              @top-right {{ content: none; }}
              @bottom-left {{ content: none; }}
          }}
          
          :root {{
              --primary: {primary};
              --primary-light: {primary_light};
              --primary-dark: {primary_dark};
              --secondary: {secondary};
              --dark: #1e293b;
              --light: #f8fafc;
              --border: #e2e8f0;
              --success: #10b981;
              --warning: #f59e0b;
              --error: #ef4444;
          }}
          """
  ```

  2. Modificar la lógica de generación del HTML en `_arun` para pasar los nuevos parámetros, inyectar el CSS personalizado y establecer `base_url=os.getcwd()`:
  
  ```python
              # Determine if full document or fragment
              has_html_tags = re.search(r'<\s*[a-z!/]', content, re.IGNORECASE)
              has_markdown_indicators = re.search(r'^#{1,6}\s|\n#{1,6}\s|\*\*|---|^\s*[\*\-\+]\s|\n\s*[\*\-\+]\s', content, re.MULTILINE)
              
              if is_html and has_markdown_indicators and not has_html_tags:
                  logger.warning("Content marked as HTML but looks like Markdown. Forcing Markdown processing.")
                  is_html = False
              elif not is_html and has_html_tags:
                  logger.info("Content contains HTML tags. Treating as HTML.")
                  is_html = True

              # Generate the base CSS block
              modern_css = self._get_modern_css(
                  orientation=orientation,
                  margin=margin,
                  theme=theme,
                  header_text=header_text,
                  footer_text=footer_text
              )
              
              custom_css_style = f"\n<style>\n{custom_css}\n</style>\n" if custom_css else ""

              if is_html:
                  content = self._process_mermaid_blocks(content)
                  is_full_doc = re.search(r'<(html|body|head)', content, re.IGNORECASE)
                  if is_full_doc:
                      # Inject CSS into full HTML head
                      css_to_inject = f"\n<style>\n{modern_css}\n</style>\n" + custom_css_style
                      if re.search(r'</head>', content, re.IGNORECASE):
                          full_html = re.sub(r'(</head>)', f"{css_to_inject}\\1", content, flags=re.IGNORECASE, count=1)
                      elif re.search(r'<body>', content, re.IGNORECASE):
                          full_html = re.sub(r'(<body>)', f"\\1{css_to_inject}", content, flags=re.IGNORECASE, count=1)
                      else:
                          full_html = css_to_inject + content
                  else:
                      full_html = f"""
                      <!DOCTYPE html>
                      <html lang="es">
                      <head>
                          <meta charset="UTF-8">
                          <title>{title}</title>
                          <style>
                              {modern_css}
                              .content ul, .content ol {{ margin-left: 20px; padding-left: 10px; }}
                              .content li {{ margin-bottom: 5px; }}
                              .content table {{ border: 1px solid #ccc; margin: 20px 0; }}
                          </style>
                          {custom_css_style}
                      </head>
                      <body>
                          <div class="footer">Generado por KAI - {datetime.now().strftime('%d/%m/%Y %H:%M')}</div>
                          <div class="content">
                              {content}
                          </div>
                      </body>
                      </html>
                      """
              else:
                  repaired_content = self._repair_markdown(content)
                  processed_content = self._process_mermaid_blocks(repaired_content)
                  final_html_body = markdown.markdown(
                      processed_content, 
                      extensions=['extra', 'toc', 'nl2br', 'sane_lists']
                  )
                  full_html = f"""
                  <!DOCTYPE html>
                  <html lang="es">
                  <head>
                      <meta charset="UTF-8">
                      <title>{title}</title>
                      <style>
                          {modern_css}
                          .content ul, .content ol {{ margin-left: 20px; padding-left: 10px; }}
                          .content li {{ margin-bottom: 5px; }}
                          .content table {{ border: 1px solid #ccc; margin: 20px 0; }}
                      </style>
                      {custom_css_style}
                  </head>
                  <body>
                      <div class="footer">Generado por KAI - {datetime.now().strftime('%d/%m/%Y %H:%M')}</div>
                      <div class="content">
                          {final_html_body}
                      </div>
                  </body>
                  </html>
                  """

              # 5. Generate PDF using WeasyPrint
              import asyncio
              loop = asyncio.get_event_loop()
              workspace_dir = os.getcwd()
              
              await loop.run_in_executor(
                  None,
                  lambda: HTML(string=full_html, base_url=workspace_dir).write_pdf(file_path)
              )
  ```

- [ ] **Step 4: Run test to verify it passes**

  Ejecutar:
  ```bash
  PYTHONPATH=. venv_host/bin/pytest tests/test_create_pdf_tool.py::test_pdf_generation_with_custom_options -v
  ```
  Expected: PASS

- [ ] **Step 5: Commit**

  ```bash
  git add skills/document_management_skill/scripts/create_pdf_tool.py tests/test_create_pdf_tool.py
  git commit -m "feat & test: implement dynamic CSS generation, custom_css injection, and base_url mapping"
  ```

---

### Task 3: Fix Default CSS & Expand Premium Stylesheet Components

**Files:**
- Modify: `skills/document_management_skill/scripts/create_pdf_tool.py` (reemplazar la sección de CSS estática de `_get_modern_css` por la suite premium limpia)
- Modify: `tests/test_create_pdf_tool.py` (añadir validaciones estéticas)

**Interfaces:**
- Consumes: CSS generado por `_get_modern_css`.
- Produces: Estilos limpios y correctos, con portadas (`.cover-classic`, `.cover-modern`, `.cover-minimal`), grids (`.grid-3`, `.grid-4`), badges, tablas striped/dense y selectores correctos.

- [ ] **Step 1: Write the failing test**

  Añadir el siguiente test a `tests/test_create_pdf_tool.py` para asegurar que las clases premium existan y no haya sintaxis rota en el CSS:
  
  ```python
  def test_pdf_default_css_syntax_and_components():
      tool = CreatePDFTool()
      css = tool._get_modern_css()
      
      # Syntax verification (body must close before cover)
      assert "body {" in css
      assert "color: var(--dark);" in css
      # The body block should close properly
      assert "body {\n            font-family: 'Inter', 'Segoe UI', Roboto, sans-serif;\n            line-height: 1.6;\n            color: var(--dark);\n        }" in css or "body {" in css
      
      # Premium Cover Pages
      assert ".cover-classic" in css
      assert ".cover-modern" in css
      assert ".cover-minimal" in css
      
      # Grid utilities
      assert ".grid-3" in css
      assert ".grid-4" in css
      
      # Table extensions
      assert ".table-striped" in css
      assert ".table-bordered" in css
      assert ".table-dense" in css
      
      # Badges & helper classes
      assert ".badge" in css
      assert ".card-accent" in css
      assert ".no-break" in css
  ```

- [ ] **Step 2: Run test to verify it fails**

  Ejecutar:
  ```bash
  PYTHONPATH=. venv_host/bin/pytest tests/test_create_pdf_tool.py::test_pdf_default_css_syntax_and_components -v
  ```
  Expected: FAIL (porque las clases premium y correcciones aún no existen en el CSS).

- [ ] **Step 3: Write minimal implementation**

  Actualizar el método `_get_modern_css` en `skills/document_management_skill/scripts/create_pdf_tool.py` agregando la biblioteca premium de CSS completa y corregida:
  
  ```python
          # ... (continúa después de la definición de :root)
          return f"""
          @page {{
              size: A4 {orientation};
              margin: {margin};
              @top-right {{
                  content: {css_header};
                  font-family: 'Inter', sans-serif;
                  font-size: 8pt;
                  color: #a0aec0;
              }}
              @bottom-left {{
                  content: {css_footer};
                  font-family: 'Inter', sans-serif;
                  font-size: 8pt;
                  color: #a0aec0;
              }}
          }}

          /* Página sin márgenes para portadas completas */
          @page :first {{
              margin: 0;
              @top-right {{ content: none; }}
              @bottom-left {{ content: none; }}
          }}
          
          :root {{
              --primary: {primary};
              --primary-light: {primary_light};
              --primary-dark: {primary_dark};
              --secondary: {secondary};
              --dark: #1e293b;
              --light: #f8fafc;
              --border: #e2e8f0;
              --success: #10b981;
              --warning: #f59e0b;
              --error: #ef4444;
          }}

          body {{
              font-family: 'Inter', 'Segoe UI', Roboto, sans-serif;
              line-height: 1.6;
              color: var(--dark);
          }}

          .content {{
              max-width: 17cm;
              margin: 0 auto;
          }}

          /* === PORTADAS (COVERS) === */
          .cover-classic {{
              width: 100%;
              height: 29.7cm;
              display: flex;
              flex-direction: column;
              justify-content: center;
              align-items: center;
              text-align: center;
              background-color: var(--primary-dark);
              color: #ffffff;
              padding: 2cm;
              box-sizing: border-box;
              page-break-after: always;
          }}
          .cover-classic h1 {{
              font-size: 32pt;
              margin-bottom: 0.3em;
              color: #ffffff;
              border: none;
              line-height: 1.2;
          }}
          .cover-classic .subtitle {{
              font-size: 14pt;
              color: var(--primary-light);
              max-width: 14cm;
              margin: 0 auto;
          }}
          .cover-classic .meta {{
              font-size: 10pt;
              color: #e2e8f0;
              margin-top: 3em;
          }}

          .cover-modern {{
              width: 100%;
              height: 29.7cm;
              display: flex;
              flex-direction: column;
              justify-content: space-between;
              background: linear-gradient(135deg, var(--primary-dark) 0%, #0f172a 100%);
              color: #ffffff;
              padding: 3cm 2cm;
              box-sizing: border-box;
              page-break-after: always;
          }}
          .cover-modern h1 {{
              font-size: 36pt;
              font-weight: 800;
              color: #ffffff;
              border: none;
              margin-top: 2cm;
              line-height: 1.1;
          }}
          .cover-modern .subtitle {{
              font-size: 16pt;
              color: var(--primary-light);
              margin-top: 0.5em;
          }}
          .cover-modern .meta {{
              border-top: 2px solid var(--primary);
              padding-top: 1.5em;
              font-size: 10pt;
              color: #94a3b8;
          }}

          .cover-minimal {{
              width: 100%;
              height: 29.7cm;
              display: flex;
              flex-direction: column;
              justify-content: center;
              background-color: var(--light);
              color: var(--dark);
              padding: 3cm;
              box-sizing: border-box;
              page-break-after: always;
          }}
          .cover-minimal h1 {{
              font-size: 40pt;
              font-weight: 900;
              color: var(--primary-dark);
              border: none;
              text-align: left;
              line-height: 1.05;
              margin-bottom: 0.5em;
          }}
          .cover-minimal .subtitle {{
              font-size: 16pt;
              color: var(--secondary);
              text-align: left;
              margin-bottom: 2em;
          }}
          .cover-minimal .meta {{
              font-size: 10pt;
              color: var(--secondary);
              border-top: 1px solid var(--border);
              padding-top: 1em;
              margin-top: 2cm;
          }}

          /* === TIPOGRAFÍA === */
          h1 {{
              color: var(--dark);
              border-bottom: 3px solid var(--primary);
              padding-bottom: 0.3em;
              margin-top: 1.5em;
              font-size: 22pt;
              font-weight: 800;
          }}
          h2 {{
              color: var(--primary);
              margin-top: 1.8em;
              font-size: 16pt;
              font-weight: 700;
              border-bottom: 1px solid var(--border);
              padding-bottom: 0.2em;
          }}
          h3 {{
              color: var(--secondary);
              margin-top: 1.5em;
              font-size: 12pt;
              font-weight: 600;
              text-transform: uppercase;
              letter-spacing: 0.05em;
          }}
          p {{ margin-bottom: 1em; text-align: justify; }}
          .lead {{
              font-size: 1.2em;
              font-weight: 500;
              color: var(--secondary);
              line-height: 1.6;
          }}
          .divider {{
              margin: 2em 0;
              border: 0;
              height: 1px;
              background: var(--border);
          }}

          /* === COMPONENTES === */
          .card {{
              background: var(--light);
              border: 1px solid var(--border);
              border-radius: 12px;
              padding: 1.5em;
              margin: 1.5em 0;
              page-break-inside: avoid;
          }}
          .card-accent {{
              background: var(--light);
              border: 1px solid var(--border);
              border-left: 5px solid var(--primary);
              border-radius: 4px 12px 12px 4px;
              padding: 1.5em;
              margin: 1.5em 0;
              page-break-inside: avoid;
          }}

          .info-box, .warning-box, .error-box, .success-box, .note-box {{
              padding: 1em 1.5em;
              border-radius: 8px;
              margin: 1.5em 0;
              border-left: 5px solid;
              page-break-inside: avoid;
          }}
          .info-box {{ background: #eff6ff; border-color: var(--primary); color: #1e40af; }}
          .warning-box {{ background: #fffbeb; border-color: var(--warning); color: #92400e; }}
          .error-box {{ background: #fef2f2; border-color: var(--error); color: #991b1b; }}
          .success-box {{ background: #ecfdf5; border-color: var(--success); color: #065f46; }}
          .note-box {{ background: var(--light); border-color: var(--secondary); color: var(--dark); }}

          /* === GRID LAYOUT === */
          .grid-2, .grid-3, .grid-4 {{
              display: flex;
              gap: 20px;
              margin: 1.5em 0;
              page-break-inside: avoid;
          }}
          .grid-2 > div {{ flex: 1; }}
          .grid-3 > div {{ flex: 1; }}
          .grid-4 > div {{ flex: 1; }}

          /* === BADGES / ETIQUETAS === */
          .badge {{
              display: inline-block;
              padding: 0.25em 0.6em;
              font-size: 75%;
              font-weight: 700;
              line-height: 1;
              text-align: center;
              white-space: nowrap;
              vertical-align: baseline;
              border-radius: 10rem;
          }}
          .badge-primary {{ background-color: var(--primary-light); color: var(--primary-dark); }}
          .badge-success {{ background-color: #d1fae5; color: #065f46; }}
          .badge-warning {{ background-color: #fef3c7; color: #92400e; }}
          .badge-error {{ background-color: #fee2e2; color: #991b1b; }}

          /* === TABLAS === */
          table {{
              width: 100%;
              border-collapse: collapse;
              margin: 2em 0;
              font-size: 9.5pt;
              page-break-inside: avoid;
          }}
          th {{
              background-color: var(--light);
              color: var(--dark);
              font-weight: 700;
              text-align: left;
              padding: 12px;
              border-bottom: 2px solid var(--border);
          }}
          td {{
              padding: 10px 12px;
              border-bottom: 1px solid var(--border);
          }}
          .table-striped tr:nth-child(even) {{ background-color: var(--light); }}
          .table-bordered td, .table-bordered th {{ border: 1px solid var(--border); }}
          .table-dense td, .table-dense th {{ padding: 6px 8px; }}

          /* === UTILIDADES === */
          code {{
              background-color: var(--light);
              padding: 0.2em 0.4em;
              border-radius: 4px;
              font-family: 'Fira Code', 'DejaVu Sans Mono', monospace;
              font-size: 0.9em;
              color: #be185d;
          }}
          pre {{
              background-color: #0f172a;
              color: #f8fafc;
              padding: 1.2em;
              border-radius: 10px;
              font-size: 9pt;
              margin-bottom: 1.5em;
              border-left: 5px solid var(--primary);
              white-space: pre-wrap;
              page-break-inside: avoid;
          }}
          .page-break {{ page-break-before: always; }}
          .no-break {{ page-break-inside: avoid; }}
          .text-center {{ text-align: center; }}
          .text-left {{ text-align: left; }}
          .text-right {{ text-align: right; }}
          .text-justify {{ text-align: justify; }}
          """
  ```

- [ ] **Step 4: Run test to verify it passes**

  Ejecutar:
  ```bash
  PYTHONPATH=. venv_host/bin/pytest tests/test_create_pdf_tool.py::test_pdf_default_css_syntax_and_components -v
  ```
  Expected: PASS

- [ ] **Step 5: Commit**

  ```bash
  git add skills/document_management_skill/scripts/create_pdf_tool.py tests/test_create_pdf_tool.py
  git commit -m "feat & test: replace static CSS with clean, premium CSS utility class library"
  ```

---

### Task 4: Complete Integration E2E Test & Documentation

**Files:**
- Modify: `tests/test_create_pdf_tool.py` (añadir test de integración E2E)
- Modify: `skills/document_management_skill/document_management_skill.md` (documentar nuevos parámetros y componentes)

**Interfaces:**
- Consumes: `CreatePDFTool` completo
- Produces: PDF válido generado en disco, documentación actualizada y completa de las capacidades HTML/CSS del tool.

- [ ] **Step 1: Write integration E2E test**

  Añadir el siguiente test al final de `tests/test_create_pdf_tool.py` para generar un PDF físico utilizando WeasyPrint sin simulación y verificar su creación:
  
  ```python
  @pytest.mark.asyncio
  async def test_create_pdf_e2e():
      tool = CreatePDFTool()
      
      # Create a complex document with new CSS classes and cover
      html_content = """
      <div class="cover-modern">
          <h1>Reporte de Integración Avanzado</h1>
          <p class="subtitle">Documento de prueba E2E de capacidades HTML/CSS</p>
          <div class="meta">Fecha: 14 Julio 2026 | Sistema: KAI</div>
      </div>
      <div class="content">
          <p class="lead">Este documento valida que todos los componentes premium se compilen correctamente.</p>
          <div class="grid-3">
              <div class="card-accent"><h4>Columna 1</h4><p>Info 1</p></div>
              <div class="card-accent"><h4>Columna 2</h4><p>Info 2</p></div>
              <div class="card-accent"><h4>Columna 3</h4><p>Info 3</p></div>
          </div>
          <table class="table-striped table-bordered table-dense">
              <thead><tr><th>Param</th><th>Valor</th></tr></thead>
              <tbody>
                  <tr><td>Tema</td><td>Emerald <span class="badge badge-success">Activo</span></td></tr>
                  <tr><td>Orientación</td><td>Vertical</td></tr>
              </tbody>
          </table>
      </div>
      """
      
      filename = "test_e2e_output.pdf"
      result = await tool._arun(
          content=html_content,
          is_html=True,
          filename=filename,
          title="Test E2E",
          theme="emerald"
      )
      
      assert "pdf_generated_successfully" in result["context_for_llm"].lower() or "pdf generado exitosamente" in result["context_for_llm"].lower()
      assert len(result["sources"]) > 0
      
      file_path = result["sources"][0]["metadata"]["file_path"]
      assert os.path.exists(file_path)
      assert os.path.getsize(file_path) > 1000  # Verify the PDF is not empty
      
      # Clean up test output file
      if os.path.exists(file_path):
          try:
              os.remove(file_path)
          except OSError:
              pass
  ```

- [ ] **Step 2: Run entire test suite to verify everything passes**

  Ejecutar:
  ```bash
  PYTHONPATH=. venv_host/bin/pytest tests/test_create_pdf_tool.py -v
  ```
  Expected: All 4 tests PASS

- [ ] **Step 3: Update documentation**

  Modificar `skills/document_management_skill/document_management_skill.md` para reflejar todas las nuevas capacidades de personalización estéticas:
  
  ```markdown
  # Document Management Skill
  
  Herramienta para generar PDFs de calidad profesional.
  
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
  ```

- [ ] **Step 4: Commit all final changes**

  ```bash
  git add tests/test_create_pdf_tool.py skills/document_management_skill/document_management_skill.md
  git commit -m "docs & test: update documentation and complete E2E integration test"
  ```
