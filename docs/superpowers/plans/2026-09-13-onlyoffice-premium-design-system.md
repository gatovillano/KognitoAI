# OnlyOffice Premium Design System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a comprehensive, modular premium design system for OnlyOffice documents (Word, Excel, PowerPoint) in KAI, including unified themes, executive cover pages, callouts, KPI cards, native charts, modular slide layouts, a master templates catalog, and tool integration.

**Architecture:** A decoupled `skills/onlyoffice_skill/design/` package containing `themes.py`, `docx_engine.py`, `xlsx_engine.py`, `pptx_engine.py`, and `template_registry.py`. Tools `create_onlyoffice_document_tool` and `edit_onlyoffice_document_tool` delegate to these engines while maintaining full backward compatibility.

**Tech Stack:** Python 3.11+, python-docx, openpyxl, python-pptx, LangChain BaseTool, Pydantic, pytest.

## Global Constraints
- Must not break existing document creation or editing workflows.
- Must preserve all existing actions in `edit_onlyoffice_document_tool.py`.
- Must handle missing dependencies gracefully (DOCX_AVAILABLE, XLSX_AVAILABLE, PPTX_AVAILABLE).
- Files created must be 100% valid OOXML readable by OnlyOffice Document Server without schema warnings.

---

### Task 1: Package Scaffolding & Unified Theme System (`themes.py`)

**Files:**
- Create: `skills/onlyoffice_skill/design/__init__.py`
- Create: `skills/onlyoffice_skill/design/themes.py`
- Test: `tests/test_onlyoffice_themes.py`

**Interfaces:**
- Produces: `get_theme(theme_name: str) -> dict`, `hex_to_rgb(hex_str: str) -> tuple`, `THEMES: dict`.

- [ ] **Step 1: Write test for themes**
- [ ] **Step 2: Implement themes.py**
- [ ] **Step 3: Run test and verify**
- [ ] **Step 4: Commit**

---

### Task 2: Word Engine (`docx_engine.py`)

**Files:**
- Create: `skills/onlyoffice_skill/design/docx_engine.py`
- Test: `tests/test_onlyoffice_docx_engine.py`

**Interfaces:**
- Produces:
  - `add_cover_page(doc, title, subtitle, author, organization, date_str, theme, style)`
  - `render_callout(doc, callout_type, text, theme)`
  - `add_kpi_cards(doc, cards, theme)`
  - `add_page_number_footer(doc, doc_title, confidentiality)`

- [ ] **Step 1: Write test for docx_engine**
- [ ] **Step 2: Implement docx_engine.py**
- [ ] **Step 3: Run test and verify**
- [ ] **Step 4: Commit**

---

### Task 3: Excel Engine (`xlsx_engine.py`)

**Files:**
- Create: `skills/onlyoffice_skill/design/xlsx_engine.py`
- Test: `tests/test_onlyoffice_xlsx_engine.py`

**Interfaces:**
- Produces:
  - `add_kpi_cards(sheet, cards, theme, start_row, start_col)`
  - `add_chart(sheet, chart_type, data_range, categories_range, target_cell, title, theme, width, height)`
  - `apply_conditional_formatting(sheet, range_address, rule_type, options)`

- [ ] **Step 1: Write test for xlsx_engine**
- [ ] **Step 2: Implement xlsx_engine.py**
- [ ] **Step 3: Run test and verify**
- [ ] **Step 4: Commit**

---

### Task 4: PowerPoint Engine (`pptx_engine.py`)

**Files:**
- Create: `skills/onlyoffice_skill/design/pptx_engine.py`
- Test: `tests/test_onlyoffice_pptx_engine.py`

**Interfaces:**
- Produces:
  - `add_slide(prs, layout_type, data, theme, speaker_notes)`
  - `add_table(slide, table_data, theme, left, top, width, height)`

- [ ] **Step 1: Write test for pptx_engine**
- [ ] **Step 2: Implement pptx_engine.py**
- [ ] **Step 3: Run test and verify**
- [ ] **Step 4: Commit**

---

### Task 5: Master Templates Catalog (`template_registry.py`)

**Files:**
- Create: `skills/onlyoffice_skill/design/template_registry.py`
- Test: `tests/test_onlyoffice_template_registry.py`

**Interfaces:**
- Produces:
  - `get_template_info(template_id: str) -> dict`
  - `list_templates() -> list`
  - `create_from_template(template_id, file_path, title, subtitle, theme_name)`

- [ ] **Step 1: Write test for template_registry**
- [ ] **Step 2: Implement template_registry.py**
- [ ] **Step 3: Run test and verify**
- [ ] **Step 4: Commit**

---

### Task 6: Tool Integrations & Skill Documentation

**Files:**
- Modify: `skills/onlyoffice_skill/scripts/create_onlyoffice_document_tool.py`
- Modify: `skills/onlyoffice_skill/scripts/edit_onlyoffice_document_tool.py`
- Modify: `skills/onlyoffice_skill/SKILL.md`
- Test: `tests/test_onlyoffice_tools_integration.py`

- [ ] **Step 1: Update create_onlyoffice_document_tool.py**
- [ ] **Step 2: Update edit_onlyoffice_document_tool.py with new actions and callout parsing**
- [ ] **Step 3: Update SKILL.md with complete documentation and examples**
- [ ] **Step 4: Run all integration tests and verify full suite**
- [ ] **Step 5: Commit**
