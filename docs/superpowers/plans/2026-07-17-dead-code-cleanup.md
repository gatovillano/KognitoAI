# Dead Code & Legacy Cleanups Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Purge duplicate backups, temporary draft files, and obsolete legacy endpoints from KognitoAI.

**Architecture:** We will delete the 5 identified backup/temporary files, delete the legacy `api/openai.py` file, and remove the import reference in `api/main.py`. Finally, we compile and verify main.py.

**Tech Stack:** Python 3, Git

## Global Constraints

- Deletion must be permanent in the active tree (tracked via git).
- The compiler check on `api/main.py` must succeed.

---

### Task 1: Delete Backup & Temporary Files

**Files:**
- Delete: `core/agents/deep_researcher_langgraph_backup.py`
- Delete: `core/prompt_manager.py.new`
- Delete: `api/caldav.py.bak_20260312_020244`
- Delete: `api/caldav.py.bak_20260312_020339`
- Delete: `api/main.py.bak`

**Interfaces:**
- Consumes: None
- Produces: None

- [ ] **Step 1: Delete deep_researcher_langgraph_backup.py**
  Run: `rm -f core/agents/deep_researcher_langgraph_backup.py`
- [ ] **Step 2: Delete prompt_manager.py.new**
  Run: `rm -f core/prompt_manager.py.new`
- [ ] **Step 3: Delete caldav.py backups**
  Run: `rm -f api/caldav.py.bak_20260312_020244 api/caldav.py.bak_20260312_020339`
- [ ] **Step 4: Delete main.py.bak**
  Run: `rm -f api/main.py.bak`
- [ ] **Step 5: Verify all deleted files are gone**
  Run: `git status`
  Expected: Shows deletions of these tracked files (or untracked files are no longer present).
- [ ] **Step 6: Commit deletions**
  ```bash
  git add core/agents/deep_researcher_langgraph_backup.py core/prompt_manager.py.new api/caldav.py.bak_20260312_020244 api/caldav.py.bak_20260312_020339 api/main.py.bak
  git commit -m "refactor: delete temporary draft and backup files"
  ```

---

### Task 2: Remove Legacy Router and main.py Import

**Files:**
- Modify: `api/main.py`
- Delete: `api/openai.py`

**Interfaces:**
- Consumes: None
- Produces: Cleaned routing imports in api/main.py

- [ ] **Step 1: Delete api/openai.py**
  Run: `rm -f api/openai.py`
- [ ] **Step 2: Remove import from api/main.py**
  Modify [api/main.py](file:///home/gato/Proyectos/KognitoAI/kognito-ai/api/main.py#L394) by removing the line:
  ```python
  from api.openai import router as openai_router # IMPORTAR OPENAI COMPATIVEL (legacy)
  ```
- [ ] **Step 3: Verify syntax compilation**
  Run: `.venv/bin/python -m py_compile api/main.py`
  Expected: Successful compilation without errors.
- [ ] **Step 4: Commit router deletion and cleanup**
  ```bash
  git add api/main.py api/openai.py
  git commit -m "refactor: delete legacy api/openai.py router and clean up main.py imports"
  ```

---

### Task 3: Run Verification

**Files:**
- Test: `tests/`

**Interfaces:**
- Consumes: None
- Produces: Test verification status

- [ ] **Step 1: Run pytest compilation check**
  Run: `.venv/bin/python -m py_compile api/main.py`
  Expected: Success.
- [ ] **Step 2: Verify git status is clean**
  Run: `git status`
  Expected: No untracked/unstaged changes.
