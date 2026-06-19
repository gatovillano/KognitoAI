---
name: onlyoffice-rag-pipeline
description: |
  Pipeline para integrar documentos de OnlyOffice con el sistema RAG de KAI.
  Procesa documentos, genera embeddings y los almacena en el conocimiento.
---

## Objetivo
Crear un pipeline que integre los documentos de OnlyOffice con el sistema de conocimiento de KAI.

## Cuándo Usarlo
- Cuando un documento de OnlyOffice necesita ser searchable por RAG
- Para indexar documentos existentes en masa
- Para procesar documentos con texto estructurado

## Flujo de Trabajo
1. Buscar documentos en OnlyOffice
2. Extraer texto del documento
3. Dividir en chunks con overlap
4. Generar embeddings
5. Almacenar en pgvector y Neo4j

## Uso Básico

```python
from skills.onlyoffice_rag_pipeline.scripts.process_document import ProcessOnlyOfficeDocumentTool

tool = ProcessOnlyOfficeDocumentTool(
    account_id="fdde7eb8-3c4e-405f-aa5e-659259e10268"
)

result = await tool.arun(
    document_id="uuid-del-documento",
    chunk_size=128,
    overlap=20
)
```

## Parámetros

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| document_id | str | Sí | ID del documento en OnlyOffice |
| chunk_size | int | No | Tamaño de chunks (default: 128) |
| overlap | int | No | Solapamiento (default: 20) |
| workspace_id | str | No | ID del workspace (para procesar todos) |

## Estado
- ✅ Extracción de texto
- ✅ Generación de embeddings
- ✅ Indexación en pgvector
- ✅ Almacenamiento en Neo4j
