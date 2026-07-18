# Design Document: Sub-project 1 — Quick Wins & Code Hygiene

**Date:** 2026-07-17  
**Scope:** `core/agent.py`, `core/agents_langgraph_backup/`  
**Status:** Approved by User  

---

## 1. Goal Description

Address immediate hygiene issues in the codebase identified in [code_smells_report.md](file:///home/gato/Proyectos/KognitoAI/kognito-ai/docs/code_smells_report.md):
1. Delete redundant backup files in `core/agents_langgraph_backup/`.
2. Fix 4 bare `except:` blocks in `core/agent.py` which swallow errors.
3. Clean up unused imports and lines > 100 characters in `core/agent.py`.

---

## 2. Proposed Changes

### 2.1 File Deletion
* Delete the entire folder [core/agents_langgraph_backup/](file:///home/gato/Proyectos/KognitoAI/kognito-ai/core/agents_langgraph_backup/).

### 2.2 Exception Handling (Replacing Bare Excepts)
In [core/agent.py](file:///home/gato/Proyectos/KognitoAI/kognito-ai/core/agent.py):
* **Line 2149 & 2166**: Replace `except:` with `except json.JSONDecodeError:` so that only JSON decoding errors on partial chunks are ignored.
* **Line 2410**: Replace `except:` with `except json.JSONDecodeError:` and log the JSON parsing warnings.
* **Line 2725**: Replace `except:` with `except json.JSONDecodeError:`.

### 2.3 Automated Import Optimization & Styling
* Install `ruff` inside `.venv` (`.venv/bin/pip install ruff`).
* Run `ruff check --select F401 --fix core/agent.py` to remove unused imports.
* Run `ruff format core/agent.py` to automatically wrap lines according to standard style.

---

## 3. Verification Plan

### Automated Tests
* Verify syntax using python's built-in compile module:
  ```bash
  .venv/bin/python -m py_compile core/agent.py
  ```
* Run any existing tests to ensure agent behavior is preserved:
  ```bash
  .venv/bin/pytest
  ```
