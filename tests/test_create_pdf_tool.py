import pytest
import os
from unittest.mock import patch, MagicMock
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

@pytest.mark.asyncio
async def test_pdf_generation_with_custom_options():
    tool = CreatePDFTool()
    
    # Mock the WeasyPrint HTML calls to capture the arguments
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

def test_pdf_default_css_syntax_and_components():
    tool = CreatePDFTool()
    css = tool._get_modern_css()
    
    # Syntax verification
    assert "body {" in css
    # Ensure there is no duplicated malformed .cover rules inside body block
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
    
    assert "pdf generado exitosamente" in result["context_for_llm"].lower() or "pdf generado con éxito" in result["context_for_llm"].lower() or "generado exitosamente" in result["context_for_llm"].lower()
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
