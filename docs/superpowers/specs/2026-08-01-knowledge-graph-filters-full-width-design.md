# Design Specification: Dynamic Graph Filters & Full Width Layout

**Date**: 2026-08-01  
**Topic**: Knowledge Graph Filters Scoping & Full-Width Layout Expansion  

## Overview
This design updates the Knowledge Graph interface in the RAG section to:
1. Dynamically calculate available filter types (node types and edge types) from the graph dataset currently loaded in memory, ensuring only visible/loaded entity types appear in the filter panel.
2. Remove fixed max-width constraints (`max-w-7xl mx-auto`) and side margins from the RAG / Knowledge Graph page so it occupies the full available width of the screen.

---

## 1. Dynamic Graph Filters

### Problem
Previously, graph filters fetched metadata globally or per dataset from the backend endpoint `/api/knowledge-graph/metadata`. If a dataset contained only a few node types or if graph data was limited, the filter list could show entity types or relationship types not present in the current dataset or view, confusing the user.

### Solution
In `src/components/GraphView.tsx` (`useKnowledgeGraph` hook):
- Compute `computedMetadata` dynamically whenever `originalGraphData` changes:
  - **Node Types**: Iterate over `originalGraphData.nodes`, group by `node.type || 'Desconocido'`, count instances, and sort descending by count.
  - **Edge Types**: Iterate over `originalGraphData.edges`, group by `edge.type || edge.label || 'RELACIONADO'`, count instances, and sort descending by count.
- Merge or override `metadata` with this computed structure when `originalGraphData` is present.
- Pass `computedMetadata` to `GraphFilters` so only types present in the loaded dataset/view appear in the filter checkboxes.

---

## 2. Full-Width Layout Expansion

### Problem
The RAG page container in `src/app/(dashboard)/rag/page.tsx` was wrapped in `max-w-7xl mx-auto`, restricting the horizontal space and centering the content with wide side margins on high-resolution displays.

### Solution
- In `src/app/(dashboard)/rag/page.tsx`:
  - Replace `max-w-7xl mx-auto` with `w-full` and adjust padding to `p-2 sm:p-4 md:p-6 w-full`.
- In `src/components/GraphView.tsx`:
  - Ensure top container uses `w-full h-full p-2 sm:p-4` to maximize canvas and filter panel area.

---

## Verification Plan

### Automated Tests
- Run `npx tsc --noEmit` to verify type safety.

### Manual Verification
1. Open the Knowledge Graph tab under `/rag`.
2. Select different datasets and verify that the filter sidebar updates dynamically to display ONLY the node types and relationship types contained in the selected dataset.
3. Confirm that the page layout spans the full available width without horizontal scrolling or artificial max-width side margins.
