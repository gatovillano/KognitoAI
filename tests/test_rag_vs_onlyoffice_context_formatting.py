import pytest
from core.prompt_manager import _format_selected_context_items, PromptManager

def test_format_selected_context_items_rag_and_onlyoffice():
    items = [
        {
            "id": "doc-uuid-123",
            "type": "document",
            "name": "manual_usuario.pdf",
            "file_name": "manual_usuario.pdf",
            "topic": "Documentación",
            "doc_source": "rag",
        },
        {
            "id": "oo-uuid-456",
            "type": "onlyoffice",
            "name": "propuesta_comercial.docx",
            "title": "propuesta_comercial.docx",
            "topic": "OnlyOffice",
            "doc_source": "onlyoffice",
        },
        {
            "id": "col-uuid-789",
            "type": "collection",
            "name": "Investigación Mercado",
            "topic": "Investigación Mercado",
            "doc_source": "rag",
        },
    ]

    formatted = _format_selected_context_items(items)

    # 1. Comprobar que el documento RAG tiene la etiqueta y recomendaciones correspondientes
    assert "[DOCUMENTO RAG (BASE DE CONOCIMIENTO)]" in formatted
    assert "manual_usuario.pdf" in formatted
    assert "get_document_content_tool(file_name=\"manual_usuario.pdf\")" in formatted
    assert "read_onlyoffice_document" in formatted  # Prohibición explícita

    # 2. Comprobar que el documento OnlyOffice tiene la etiqueta y recomendaciones correspondientes
    assert "[DOCUMENTO ONLYOFFICE (EDITABLE)]" in formatted
    assert "propuesta_comercial.docx" in formatted
    assert "read_onlyoffice_document(document_id=\"oo-uuid-456\")" in formatted
    assert "edit_onlyoffice_document" in formatted
    assert "get_document_content_tool" in formatted  # Prohibición explícita

    # 3. Comprobar que la colección RAG se formatea adecuadamente
    assert "[COLECCIÓN RAG (BASE DE CONOCIMIENTO)]" in formatted
    assert "Investigación Mercado" in formatted
    assert "get_document_list_tool(topic=\"Investigación Mercado\")" in formatted


def test_format_selected_context_items_backward_compatibility():
    # Sesiones anteriores donde OnlyOffice venía con type="document" y topic="OnlyOffice" o prefijo en el nombre
    items = [
        {
            "id": "legacy-oo-uuid",
            "type": "document",
            "name": "[OnlyOffice] presupuesto.xlsx",
            "title": "presupuesto.xlsx",
            "topic": "OnlyOffice",
        }
    ]

    formatted = _format_selected_context_items(items)
    assert "[DOCUMENTO ONLYOFFICE (EDITABLE)]" in formatted
    assert "presupuesto.xlsx" in formatted
    assert "read_onlyoffice_document(document_id=\"legacy-oo-uuid\")" in formatted


def test_system_prompt_includes_rag_vs_onlyoffice_distinction():
    pm = PromptManager()
    prompt = pm.build_system_prompt(
        user_profile=None,
        relevant_memories="",
        summary_string="",
        custom_prompt_from_profile=None,
        workspace_prompt=None,
        tools=[],
        account_id="test-account",
        telegram_id=None,
        has_explicit_rag_context=True,
        explicit_rag_context_items=[
            {
                "id": "test-doc-id",
                "type": "document",
                "name": "informe.pdf",
                "file_name": "informe.pdf",
            },
            {
                "id": "test-oo-id",
                "type": "onlyoffice",
                "name": "datos.xlsx",
                "title": "datos.xlsx",
            }
        ]
    )

    assert "DISTINCIÓN CRÍTICA: DOCUMENTOS RAG VS DOCUMENTOS ONLYOFFICE" in prompt
    assert "CONTEXTO PRIORITARIO SELECCIONADO POR EL USUARIO" in prompt
    assert "[DOCUMENTO RAG (BASE DE CONOCIMIENTO)]" in prompt
    assert "[DOCUMENTO ONLYOFFICE (EDITABLE)]" in prompt


def test_tool_descriptions_contain_clear_distinction():
    from skills.document_management_skill.scripts.get_document_content_tool import GetDocumentContentTool
    from skills.document_management_skill.scripts.get_document_list_tool import GetDocumentListTool
    from skills.onlyoffice_skill.scripts.read_onlyoffice_document_tool import ReadOnlyOfficeDocumentTool
    from skills.onlyoffice_skill.scripts.search_onlyoffice_documents_tool import SearchOnlyOfficeDocumentsTool
    from skills.onlyoffice_skill.scripts.list_onlyoffice_documents_tool import ListOnlyOfficeDocumentsTool
    from skills.onlyoffice_skill.scripts.create_onlyoffice_document_tool import CreateOnlyOfficeDocumentTool
    from skills.onlyoffice_skill.scripts.edit_onlyoffice_document_tool import EditOnlyOfficeDocumentTool

    # RAG Tools
    assert "[BASE DE CONOCIMIENTO RAG]" in GetDocumentContentTool.model_fields["description"].default or "[BASE DE CONOCIMIENTO RAG]" in GetDocumentContentTool.description
    assert "[BASE DE CONOCIMIENTO RAG]" in GetDocumentListTool.model_fields["description"].default or "[BASE DE CONOCIMIENTO RAG]" in GetDocumentListTool.description

    # OnlyOffice Tools
    assert "[MÓDULO ONLYOFFICE DE KAI]" in ReadOnlyOfficeDocumentTool.model_fields["description"].default or "[MÓDULO ONLYOFFICE DE KAI]" in ReadOnlyOfficeDocumentTool.description
    assert "[MÓDULO ONLYOFFICE DE KAI]" in SearchOnlyOfficeDocumentsTool.model_fields["description"].default or "[MÓDULO ONLYOFFICE DE KAI]" in SearchOnlyOfficeDocumentsTool.description
    assert "[MÓDULO ONLYOFFICE DE KAI]" in ListOnlyOfficeDocumentsTool.model_fields["description"].default or "[MÓDULO ONLYOFFICE DE KAI]" in ListOnlyOfficeDocumentsTool.description
    assert "[MÓDULO ONLYOFFICE DE KAI]" in CreateOnlyOfficeDocumentTool.model_fields["description"].default or "[MÓDULO ONLYOFFICE DE KAI]" in CreateOnlyOfficeDocumentTool.description
    assert "[MÓDULO ONLYOFFICE DE KAI]" in EditOnlyOfficeDocumentTool.model_fields["description"].default or "[MÓDULO ONLYOFFICE DE KAI]" in EditOnlyOfficeDocumentTool.description


if __name__ == "__main__":
    test_format_selected_context_items_rag_and_onlyoffice()
    test_format_selected_context_items_backward_compatibility()
    test_system_prompt_includes_rag_vs_onlyoffice_distinction()
    test_tool_descriptions_contain_clear_distinction()
    print("✅ All RAG vs OnlyOffice context tests passed successfully!")
