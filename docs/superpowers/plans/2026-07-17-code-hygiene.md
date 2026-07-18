# Sub-project 1 — Code Hygiene Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clean up the redundant backup directory, replace the 4 bare except statements with specific exceptions, and run ruff to prune unused imports and format long lines in `core/agent.py`.

**Architecture:** We will proceed sequentially: purge backup files, install ruff in virtualenv, run ruff to optimize imports, manually patch the 4 bare exceptions in agent.py, run ruff formatting to auto-wrap long lines, and finally run py_compile/pytest verification.

**Tech Stack:** Python 3, `ruff`, `pytest`

## Global Constraints

- No placeholder or unfinished code.
- Unused imports must be deleted cleanly.
- Bare excepts must be replaced by specific exception types (`json.JSONDecodeError`).

---

### Task 1: Delete Backup Directory

**Files:**
- Delete: `core/agents_langgraph_backup/`

**Interfaces:**
- Consumes: None
- Produces: None

- [ ] **Step 1: Check that the directory exists**
  Run: `ls -la core/agents_langgraph_backup`
  Expected: List of python backup files is displayed.
- [ ] **Step 2: Delete the directory**
  Run: `rm -rf core/agents_langgraph_backup`
- [ ] **Step 3: Verify deletion**
  Run: `ls -la core/agents_langgraph_backup`
  Expected: error indicating directory does not exist.
- [ ] **Step 4: Commit**
  ```bash
  git add core/agents_langgraph_backup
  git commit -m "refactor: remove redundant agents_langgraph_backup folder"
  ```

---

### Task 2: Install Ruff and Prune Unused Imports

**Files:**
- Modify: `core/agent.py`

**Interfaces:**
- Consumes: None
- Produces: Sanitized `core/agent.py` imports

- [ ] **Step 1: Install Ruff**
  Run: `.venv/bin/pip install ruff`
  Expected: Ruff is installed successfully in the virtual environment.
- [ ] **Step 2: Dry-run unused import check**
  Run: `.venv/bin/ruff check --select F401 core/agent.py`
  Expected: Ruff identifies unused imports in `core/agent.py`.
- [ ] **Step 3: Autofix unused imports**
  Run: `.venv/bin/ruff check --select F401 --fix core/agent.py`
  Expected: Ruff automatically removes the unused imports.
- [ ] **Step 4: Run syntax check**
  Run: `.venv/bin/python -m py_compile core/agent.py`
  Expected: Compilation succeeds with no errors.
- [ ] **Step 5: Commit**
  ```bash
  git add core/agent.py
  git commit -m "refactor: remove unused imports in core/agent.py using ruff"
  ```

---

### Task 3: Fix 4 Bare Excepts in agent.py

**Files:**
- Modify: `core/agent.py`

**Interfaces:**
- Consumes: `core/agent.py`
- Produces: Standardized error catching for JSON decoding

- [ ] **Step 1: Replace line 2149 bare except**
  Modify [core/agent.py](file:///home/gato/Proyectos/KognitoAI/kognito-ai/core/agent.py#L2140-L2154) to:
  ```python
                                          try:
                                              # Intentar parsear el acumulado
                                              existing_tc["args"] = json.loads(
                                                  existing_tc["_args_str"]
                                              )
                                          except json.JSONDecodeError:
                                              pass
  ```
- [ ] **Step 2: Replace line 2166 bare except**
  Modify [core/agent.py](file:///home/gato/Proyectos/KognitoAI/kognito-ai/core/agent.py#L2160-L2170) to:
  ```python
                                  if new_tc["_args_str"]:
                                      try:
                                          new_tc["args"] = json.loads(new_tc["_args_str"])
                                      except json.JSONDecodeError:
                                          pass
  ```
- [ ] **Step 3: Replace line 2410 bare except**
  Modify [core/agent.py](file:///home/gato/Proyectos/KognitoAI/kognito-ai/core/agent.py#L2405-L2415) to:
  ```python
          if isinstance(args, str):
              try:
                  args = json.loads(args)
              except json.JSONDecodeError:
                  logger.warning(
                      f"⚠️ No se pudo parsear argumentos como JSON para {tc_name}: {args}"
                  )
                  args = {}
  ```
- [ ] **Step 4: Replace line 2725 bare except**
  Modify [core/agent.py](file:///home/gato/Proyectos/KognitoAI/kognito-ai/core/agent.py#L2718-L2727) to:
  ```python
              elif isinstance(output_dump, str):
                  try:
                      parsed = json.loads(output_dump)
                      context_content = parsed.get("context_for_llm", output_dump)
                      sources_list = parsed.get("sources", [])
                      visual_schema = parsed.get("visual_schema")
                      recommendations = parsed.get("recommendations", [])
                  except json.JSONDecodeError:
                      context_content = output_dump
  ```
- [ ] **Step 5: Run syntax compilation**
  Run: `.venv/bin/python -m py_compile core/agent.py`
  Expected: Successful compilation.
- [ ] **Step 6: Commit**
  ```bash
  git add core/agent.py
  git commit -m "refactor: replace bare excepts in agent.py with json.JSONDecodeError"
  ```

---

### Task 4: Auto-format Long Lines

**Files:**
- Modify: `core/agent.py`

**Interfaces:**
- Consumes: None
- Produces: Correctly formatted agent.py

- [ ] **Step 1: Auto-format the file**
  Run: `.venv/bin/ruff format core/agent.py`
  Expected: Ruff formats the code and wraps lines under the standard limit.
- [ ] **Step 2: Check syntax**
  Run: `.venv/bin/python -m py_compile core/agent.py`
  Expected: Success.
- [ ] **Step 3: Commit**
  ```bash
  git add core/agent.py
  git commit -m "style: auto-format core/agent.py with ruff"
  ```

---

### Task 5: Run Verification tests

**Files:**
- Test: `tests/`

**Interfaces:**
- Consumes: All modules
- Produces: Testing results

- [ ] **Step 1: Execute all pytest tests**
  Run: `.venv/bin/pytest`
  Expected: All existing tests pass successfully.
- [ ] **Step 2: Commit**
  ```bash
  git commit --allow-empty -m "test: verify all tests pass on clean codebase"
  ```
