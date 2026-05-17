# Writing Plans Skill

## Overview

Create comprehensive implementation plans for multi-step tasks, assuming the engineer has zero context for the codebase and questionable taste. Document everything they need to know: which files to touch, code, testing, documentation, how to test it. Give them the whole plan as bite-sized tasks.

## When to Use

- When you have a spec or requirements for a multi-step task
- Before touching code or starting implementation
- When working with engineers who have zero context about your codebase

## Key Principles

**DRY:** Don't Repeat Yourself - avoid duplicating information
**YAGNI:** You Aren't Gonna Need It - only implement what's required
**TDD:** Test-Driven Development - write tests first
**Frequent commits:** Small, focused commits

## Usage

```json
{
  "name": "writing-plans",
  "args": {
    "spec": "Detailed specification for the feature",
    "feature_name": "Name of the feature",
    "context": "Additional context about the codebase",
    "tech_stack": "Key technologies/libraries"
  }
}
```

## Output

- Comprehensive plan saved to `docs/plans/YYYY-MM-DD-feature-name.md`
- Bite-sized tasks with checkboxes for tracking
- Complete code examples for each step
- Self-review checklist
- Execution handoff options

## Sub-Skills

After creating the plan, you can use:
- `subagent-driven-development`: Dispatch fresh subagents per task
- `executing-plans`: Execute tasks inline with checkpoints