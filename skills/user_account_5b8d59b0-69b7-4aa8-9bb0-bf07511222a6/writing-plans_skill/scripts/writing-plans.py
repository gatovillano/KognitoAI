from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type, List, Optional
import os
from datetime import datetime

class InputSchema(BaseModel):
    spec: str = Field(description="The specification or requirements document for the multi-step task")
    feature_name: str = Field(description="Name of the feature to implement")
    context: Optional[str] = Field(None, description="Additional context about the codebase or problem domain")
    tech_stack: Optional[str] = Field(None, description="Key technologies/libraries to be used")

class WritingPlans(BaseTool):
    name: str = "writing-plans"
    description: str = "Create comprehensive implementation plans for multi-step tasks, assuming zero context"
    args_schema: Type[BaseModel] = InputSchema

    def _run(self, spec: str, feature_name: str, context: Optional[str] = None, tech_stack: Optional[str] = None) -> str:
        """
        Generate a comprehensive implementation plan for multi-step tasks.
        Assumes the engineer has zero context for the codebase and questionable taste.
        """
        
        # Create plan document
        plan_content = self._generate_plan(spec, feature_name, context, tech_stack)
        
        # Save to file
        filename = f"docs/plans/{datetime.now().strftime('%Y-%m-%d')}-{feature_name.lower().replace(' ', '-')}.md"
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, 'w') as f:
            f.write(plan_content)
        
        return f"Plan complete and saved to `{filename}`.\n\n{plan_content}"
    
    def _generate_plan(self, spec: str, feature_name: str, context: Optional[str], tech_stack: Optional[str]) -> str:
        """Generate the plan content with bite-sized tasks."""
        
        header = f"""# {feature_name} Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** {spec[:100]}...

**Architecture:** Document the approach for implementing this feature with clear boundaries and well-defined interfaces.

**Tech Stack:** {tech_stack or 'Key technologies/libraries'}

---

"""
        
        body = """### Task 1: Analyze Requirements and Define Interfaces

**Files:**
- Create: `docs/plans/requirements-analysis.md`

- [ ] **Step 1: Document requirements breakdown**

Break down the spec into specific, testable requirements.

- [ ] **Step 2: Define module boundaries**

Identify which components need to be created and their interfaces.

- [ ] **Step 3: Identify existing patterns**

Research how similar functionality is implemented in the codebase.

### Task 2: Setup Project Structure

**Files:**
- Create: `src/{feature_name.lower().replace(' ', '-')}/` (directory structure)
- Modify: `README.md` (if needed for documentation)

- [ ] **Step 1: Create directory structure**

Set up the necessary directories for the new feature.

- [ ] **Step 2: Create main module files**

Create the entry point files with basic structure.

- [ ] **Step 3: Add imports and exports**

Set up the necessary imports and module exports.

### Task 3: Implement Core Functionality

**Files:**
- Create: `src/{feature_name.lower().replace(' ', '-')}/core.py`

- [ ] **Step 1: Write the failing test**

```python
def test_core_functionality():
    result = core_function(input)
    assert result == expected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_core.py::test_core_functionality -v`
Expected: FAIL with "function not defined"

- [ ] **Step 3: Write minimal implementation**

```python
def core_function(input):
    return expected_result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_core.py::test_core_functionality -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_core.py src/feature/core.py
git commit -m "feat: add core functionality"
```

### Task 4: Add Error Handling and Validation

**Files:**
- Modify: `src/{feature_name.lower().replace(' ', '-')}/core.py`
- Create: `tests/test_error_handling.py`

- [ ] **Step 1: Write tests for edge cases**

```python
def test_invalid_input():
    with pytest.raises(ValueError):
        core_function(None)
```

- [ ] **Step 2: Add validation logic**

Implement input validation and error handling.

- [ ] **Step 3: Write tests for error messages**

Verify error messages are clear and helpful.

- [ ] **Step 4: Run all tests**

Run: `pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 5: Commit**

```bash
git add .
git commit -m "feat: add error handling and validation"
```

### Task 5: Documentation and Examples

**Files:**
- Create: `docs/{feature_name.lower().replace(' ', '-')}.md`
- Modify: `README.md`

- [ ] **Step 1: Write usage examples**

Create clear examples showing how to use the feature.

- [ ] **Step 2: Update main documentation**

Add the feature to the main README and documentation.

- [ ] **Step 3: Write API reference**

Document all public methods and their parameters.

- [ ] **Step 4: Create integration examples**

Show how the feature integrates with other parts of the system.

- [ ] **Step 5: Commit**

```bash
git add docs/ README.md
git commit -m "docs: add comprehensive documentation"
```

---

## Self-Review

**1. Spec coverage:** Verify each requirement is addressed in the tasks.

**2. Placeholder scan:** Ensure no TBD, TODO, or vague steps.

**3. Type consistency:** Verify all types and interfaces are consistent.

## Execution Handoff

**Plan complete. Two execution options:**

**1. Subagent-Driven (recommended)** - Fresh subagent per task, review between tasks

**2. Inline Execution** - Execute tasks in this session with checkpoints

**Which approach would you prefer?**

"""
        
        return header + body

class SubagentDrivenDevelopment(BaseTool):
    """Sub-skill for dispatching fresh subagents per task with review."""
    name: str = "subagent-driven-development"
    description: str = "Dispatch fresh subagents for task execution with two-stage review"
    
    def __init__(self):
        super().__init__()
        self.tasks_completed = []
    
    def _run(self, plan_file: str, task_number: int) -> str:
        return f"Subagent dispatched for Task {task_number}. Will handle task-by-task execution with review between tasks."

class ExecutingPlans(BaseTool):
    """Sub-skill for inline execution with checkpoints."""
    name: str = "executing-plans"
    description: str = "Execute plans inline with checkpoints for review"
    
    def _run(self, plan_file: str) -> str:
        return f"Executing plan from {plan_file} with checkpoint reviews after each task."

# Create instances for sub-skills
subagent_skill = SubagentDrivenDevelopment()
executing_skill = ExecutingPlans()