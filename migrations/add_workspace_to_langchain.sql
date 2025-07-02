-- Migración para agregar soporte de workspace a langchain_pg_embedding
-- Este script unifica el sistema de documentos en una sola tabla

-- 1. Agregar columna workspace_id a langchain_pg_embedding
ALTER TABLE langchain_pg_embedding 
ADD COLUMN workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE;

-- 2. Crear índice para mejor performance
CREATE INDEX idx_langchain_pg_embedding_workspace_id ON langchain_pg_embedding(workspace_id);

-- 3. Migrar datos de workspace_document_chunks a langchain_pg_embedding
-- (Esto requiere embeddings ya calculados en workspace_document_chunks)

-- 4. Función para migrar datos (ejecutar después de confirmar que los embeddings están)
-- INSERT INTO langchain_pg_embedding (
--     collection_id, 
--     embedding, 
--     document, 
--     cmetadata,
--     workspace_id
-- )
-- SELECT 
--     (SELECT uuid FROM langchain_pg_collection WHERE name = CONCAT('workspace_', wdc.workspace_id::text)),
--     wdc.embedding,
--     wdc.content,
--     jsonb_build_object(
--         'file_name', wdc.file_name,
--         'title', wdc.title,
--         'topic', wdc.topic,
--         'author', wdc.author,
--         'document_id', wdc.document_id::text,
--         'chunk_index', wdc.chunk_order,
--         'type', 'document_chunk',
--         'workspace_id', wdc.workspace_id::text
--     ),
--     wdc.workspace_id
-- FROM workspace_document_chunks wdc;
