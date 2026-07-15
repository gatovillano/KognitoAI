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
