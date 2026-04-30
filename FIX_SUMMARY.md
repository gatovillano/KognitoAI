# Fix Applied to Hybrid Graph Processor

## Issue
In the `_deduplicate_entities` method of `hybrid_graph_processor.py`, there was a `NameError: name 'type_i' is not defined` occurring at line 828 in the original code.

## Root Cause
The variables `type_i` and `type_j` were being referenced in a conditional statement before they were defined. The code was:

```python
if type_i == type_j or self._are_compatible_types(type_i, type_j) or entity.get("name", "").lower() == entities[j].get("name", "").lower():
```

But `type_i` and `type_j` were defined AFTER this condition on the next lines.

## Fix Applied
Moved the variable definitions before the conditional check and added safety checks for empty type values:

```python
# Encontrar todas las entidades muy similares a esta
similar_indices = []
for j in range(i + 1, len(entities)):
    if j not in processed and similarities[i][j] > threshold:
        # Verificar también que sean del mismo tipo o tipos compatibles, 
        # o simplemente nombres idénticos (lo cual indica la misma entidad)
        type_i = entity.get("type", "")
        type_j = entities[j].get("type", "")
        # Evitar error si alguna de las entidades no tiene tipo definido
        if type_i == "" or type_j == "":
            # Si falta tipo, comparar solo por nombre
            if entity.get("name", "").lower() == entities[j].get("name", "").lower():
                similar_indices.append(j)
                processed.add(j)
        elif type_i == type_j or self._are_compatible_types(type_i, type_j) or entity.get("name", "").lower() == entities[j].get("name", "").lower():
            similar_indices.append(j)
            processed.add(j)
```

## Files Modified
- `/home/gato/Proyectos/KognitoAI/kognito-ai/knowledge_graph/hybrid_graph_processor.py` (lines 822-838)

## Verification
The fix ensures that:
1. Variables are defined before use
2. Empty type values are handled gracefully by falling back to name comparison
3. The deduplication logic remains intact for normal cases