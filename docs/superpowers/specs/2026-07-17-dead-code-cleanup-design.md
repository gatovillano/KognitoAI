# Design Document: Sub-project 2 — Dead Code & Legacy Cleanups

**Date:** 2026-07-17  
**Scope:** `core/`, `api/`  
**Status:** In Progress (Spanish review context aligned)  

---

## 1. Goal Description

Clean up the repository by removing legacy, duplicate, and temporary files that clutter the codebase and remove dead imports to keep routing imports clean.

---

## 2. Proposed Changes

### 2.1 File Deletions (Backup & Temp Files)
Delete the following 5 files:
1. [deep_researcher_langgraph_backup.py](file:///home/gato/Proyectos/KognitoAI/kognito-ai/core/agents/deep_researcher_langgraph_backup.py)
2. [prompt_manager.py.new](file:///home/gato/Proyectos/KognitoAI/kognito-ai/core/prompt_manager.py.new)
3. [caldav.py.bak_20260312_020244](file:///home/gato/Proyectos/KognitoAI/kognito-ai/api/caldav.py.bak_20260312_020244)
4. [caldav.py.bak_20260312_020339](file:///home/gato/Proyectos/KognitoAI/kognito-ai/api/caldav.py.bak_20260312_020339)
5. [main.py.bak](file:///home/gato/Proyectos/KognitoAI/kognito-ai/api/main.py.bak)

### 2.2 Legacy Router Deletion & Import Cleanup
1. Delete [openai.py](file:///home/gato/Proyectos/KognitoAI/kognito-ai/api/openai.py) (legacy router replaced by `public_api.py`).
2. Remove the unused import of `openai_router` in [main.py](file:///home/gato/Proyectos/KognitoAI/kognito-ai/api/main.py#L394).

---

## 3. Verification Plan

### Automated Tests
* Run syntax checks on modified/remaining files:
  ```bash
  .venv/bin/python -m py_compile api/main.py
  ```
* Run any existing test suites:
  ```bash
  .venv/bin/pytest
  ```
