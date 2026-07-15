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
