-- Migration script to add workspace_id column to chat_threads table
ALTER TABLE chat_threads ADD COLUMN workspace_id UUID;
CREATE INDEX idx_chat_threads_workspace_id ON chat_threads(workspace_id);
ALTER TABLE chat_threads ADD CONSTRAINT fk_chat_threads_workspace FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE SET NULL;
