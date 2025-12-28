# Fix ConceptualProcessingTool Pickling Issue

## Problem
The `ConceptualProcessingTool` was failing to instantiate due to a pickling error:
```
❌ Failed to instantiate tool 'ConceptualProcessingTool': cannot pickle '_queue.SimpleQueue' object
```

This occurred because pydantic was trying to serialize dependency objects (`GraphIntegration`, `GraphDB`, `KnowledgeGraphService`) that contain unpicklable SimpleQueue objects.

## Solution
Modified the `ConceptualProcessingTool` to:

1. **Exclude problematic dependencies from serialization** by using `Field(exclude=True)`
2. **Lazy load dependencies** when needed using getter methods
3. **Use object.__setattr__** to bypass pydantic's field assignment restrictions
4. **Fix logger initialization order** in `core/tools.py`

## Changes Made

### 1. ConceptualProcessingTool (`tools/conceptual_processing_tool.py`)
- Added `Field(exclude=True)` to dependency fields to prevent serialization
- Implemented lazy loading with `_get_graph_integration()` and `_get_knowledge_graph_service()`
- Used `object.__setattr__()` to set private attributes that bypass pydantic validation
- Updated error handling for missing dependencies

### 2. Core Tools (`core/tools.py`)
- Moved logger initialization to the top of the file to fix `NameError: name 'logger' is not defined`

## Testing
Created test scripts to verify:
- Basic instantiation works without pickling errors
- Dependencies can be injected without causing serialization issues
- Tool can be pickled and unpickled successfully

## Impact
- Resolves the instantiation failure of ConceptualProcessingTool
- Maintains backward compatibility
- No breaking changes to the tool's API
- Improves reliability of the tool system