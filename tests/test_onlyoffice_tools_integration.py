import pytest
import os
import uuid
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from skills.onlyoffice_skill.scripts.create_onlyoffice_document_tool import CreateOnlyOfficeDocumentTool
from skills.onlyoffice_skill.scripts.edit_onlyoffice_document_tool import EditOnlyOfficeDocumentTool

@pytest.mark.asyncio
async def test_create_and_edit_docx_integration():
    with tempfile.TemporaryDirectory() as tmpdir:
        acc_id = str(uuid.uuid4())
        doc_id = uuid.uuid4()

        mock_doc = MagicMock()
        mock_doc.id = doc_id
        mock_doc.account_id = uuid.UUID(acc_id)
        mock_doc.filename = "informe.docx"
        mock_doc.extension = "docx"
        mock_doc.file_path = "relative/path/informe.docx"

        with patch("skills.onlyoffice_skill.scripts.create_onlyoffice_document_tool.ensure_onlyoffice_account_dir", return_value=Path(tmpdir)), \
             patch("skills.onlyoffice_skill.scripts.create_onlyoffice_document_tool.SessionLocal") as mock_create_db, \
             patch("skills.onlyoffice_skill.scripts.edit_onlyoffice_document_tool.SessionLocal") as mock_edit_db, \
             patch("skills.onlyoffice_skill.scripts.edit_onlyoffice_document_tool.resolve_onlyoffice_file_path") as mock_resolve:

            session_create = AsyncMock()
            session_create.add = MagicMock()
            mock_create_db.return_value.__aenter__.return_value = session_create

            tool_create = CreateOnlyOfficeDocumentTool(account_id=acc_id)
            res_create = await tool_create._arun(
                name="informe.docx",
                template="executive_report",
                theme="corporate_blue",
                title="Informe Anual"
            )
            assert "creado con éxito" in res_create
            created_files = list(Path(tmpdir).glob("*.docx"))
            assert len(created_files) == 1
            actual_file_path = str(created_files[0])
            mock_resolve.return_value = actual_file_path

            session_edit = AsyncMock()
            result_mock = MagicMock()
            result_mock.scalar_one_or_none.return_value = mock_doc
            session_edit.execute.return_value = result_mock
            mock_edit_db.return_value.__aenter__.return_value = session_edit

            tool_edit = EditOnlyOfficeDocumentTool(account_id=acc_id)

            # Test markdown callout
            md_text = "> [!TIP] Esta es una recomendación clave para el equipo."
            res_append = await tool_edit._arun(
                document_id=str(doc_id),
                action="append",
                text=md_text
            )
            assert "✅ Contenido (Markdown parsed) añadido" in res_append

            # Test docx_add_kpi_cards
            res_kpis = await tool_edit._arun(
                document_id=str(doc_id),
                action="docx_add_kpi_cards",
                table_data=[["Nuevos Leads", "450", "+12%"], ["Conversión", "4.8%", "+0.5%"]]
            )
            assert "tarjetas de métricas/KPI añadidas" in res_kpis


@pytest.mark.asyncio
async def test_create_and_edit_pptx_integration():
    with tempfile.TemporaryDirectory() as tmpdir:
        acc_id = str(uuid.uuid4())
        doc_id = uuid.uuid4()

        mock_doc = MagicMock()
        mock_doc.id = doc_id
        mock_doc.account_id = uuid.UUID(acc_id)
        mock_doc.filename = "pitch.pptx"
        mock_doc.extension = "pptx"
        mock_doc.file_path = "relative/path/pitch.pptx"

        with patch("skills.onlyoffice_skill.scripts.create_onlyoffice_document_tool.ensure_onlyoffice_account_dir", return_value=Path(tmpdir)), \
             patch("skills.onlyoffice_skill.scripts.create_onlyoffice_document_tool.SessionLocal") as mock_create_db, \
             patch("skills.onlyoffice_skill.scripts.edit_onlyoffice_document_tool.SessionLocal") as mock_edit_db, \
             patch("skills.onlyoffice_skill.scripts.edit_onlyoffice_document_tool.resolve_onlyoffice_file_path") as mock_resolve:

            session_create = AsyncMock()
            session_create.add = MagicMock()
            mock_create_db.return_value.__aenter__.return_value = session_create

            tool_create = CreateOnlyOfficeDocumentTool(account_id=acc_id)
            res_create = await tool_create._arun(
                name="pitch.pptx",
                template="pitch_deck",
                theme="dark_slate"
            )
            assert "creado con éxito" in res_create
            created_files = list(Path(tmpdir).glob("*.pptx"))
            assert len(created_files) == 1
            actual_file_path = str(created_files[0])
            mock_resolve.return_value = actual_file_path

            session_edit = AsyncMock()
            result_mock = MagicMock()
            result_mock.scalar_one_or_none.return_value = mock_doc
            session_edit.execute.return_value = result_mock
            mock_edit_db.return_value.__aenter__.return_value = session_edit

            tool_edit = EditOnlyOfficeDocumentTool(account_id=acc_id)
            res_slide = await tool_edit._arun(
                document_id=str(doc_id),
                action="pptx_add_slide",
                text="Nueva Diapositiva de Prueba",
                search_text="content",
                list_items=["Primer punto", "Segundo punto"]
            )
            assert "añadida a 'pitch.pptx'" in res_slide


@pytest.mark.asyncio
async def test_create_and_edit_xlsx_integration():
    with tempfile.TemporaryDirectory() as tmpdir:
        acc_id = str(uuid.uuid4())
        doc_id = uuid.uuid4()

        mock_doc = MagicMock()
        mock_doc.id = doc_id
        mock_doc.account_id = uuid.UUID(acc_id)
        mock_doc.filename = "tablero.xlsx"
        mock_doc.extension = "xlsx"
        mock_doc.file_path = "relative/path/tablero.xlsx"

        with patch("skills.onlyoffice_skill.scripts.create_onlyoffice_document_tool.ensure_onlyoffice_account_dir", return_value=Path(tmpdir)), \
             patch("skills.onlyoffice_skill.scripts.create_onlyoffice_document_tool.SessionLocal") as mock_create_db, \
             patch("skills.onlyoffice_skill.scripts.edit_onlyoffice_document_tool.SessionLocal") as mock_edit_db, \
             patch("skills.onlyoffice_skill.scripts.edit_onlyoffice_document_tool.resolve_onlyoffice_file_path") as mock_resolve:

            session_create = AsyncMock()
            session_create.add = MagicMock()
            mock_create_db.return_value.__aenter__.return_value = session_create

            tool_create = CreateOnlyOfficeDocumentTool(account_id=acc_id)
            res_create = await tool_create._arun(
                name="tablero.xlsx",
                template="sales_dashboard",
                theme="emerald_green"
            )
            assert "creado con éxito" in res_create
            created_files = list(Path(tmpdir).glob("*.xlsx"))
            assert len(created_files) == 1
            actual_file_path = str(created_files[0])
            mock_resolve.return_value = actual_file_path

            session_edit = AsyncMock()
            result_mock = MagicMock()
            result_mock.scalar_one_or_none.return_value = mock_doc
            session_edit.execute.return_value = result_mock
            mock_edit_db.return_value.__aenter__.return_value = session_edit

            tool_edit = EditOnlyOfficeDocumentTool(account_id=acc_id)
            res_chart = await tool_edit._arun(
                document_id=str(doc_id),
                action="xlsx_add_chart",
                range_address="D8:D13",
                search_text="column",
                text="Gráfico de Prueba"
            )
            assert "insertado en la celda" in res_chart
