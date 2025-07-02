-- Script de migración para añadir columnas faltantes a la tabla workspace_document_chunks
-- Este script agrega las columnas file_name, title, topic y author si no existen.

ALTER TABLE workspace_document_chunks
ADD COLUMN IF NOT EXISTS file_name VARCHAR(255) NULL,
ADD COLUMN IF NOT EXISTS title VARCHAR(255) NULL,
ADD COLUMN IF NOT EXISTS topic VARCHAR(255) NULL,
ADD COLUMN IF NOT EXISTS author VARCHAR(255) NULL;

-- Confirmación de los cambios
COMMENT ON COLUMN workspace_document_chunks.file_name IS 'Nombre del archivo del documento.';
COMMENT ON COLUMN workspace_document_chunks.title IS 'Título del documento.';
COMMENT ON COLUMN workspace_document_chunks.topic IS 'Tema o categoría del documento.';
COMMENT ON COLUMN workspace_document_chunks.author IS 'Autor del documento.';
