-- migration_add_is_admin_to_accounts.sql

ALTER TABLE accounts
ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT FALSE;

-- Opcional: Si quieres establecer un usuario existente como admin
-- UPDATE accounts
-- SET is_admin = TRUE
-- WHERE id = 'TU_UUID_DE_ADMIN';
