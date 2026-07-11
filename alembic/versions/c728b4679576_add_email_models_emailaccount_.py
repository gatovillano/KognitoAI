"""Add email models: EmailAccount, EmailFolder, Email, EmailAttachment

Revision ID: c728b4679576
Revises: c86fba2706a2
Create Date: 2026-07-11 03:51:52.431804

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c728b4679576'
down_revision: Union[str, Sequence[str], None] = 'c86fba2706a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'email_accounts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('account_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False, comment="Nombre amigable para la cuenta (ej. 'Personal Gmail')"),
        sa.Column('email_address', sa.String(length=255), nullable=False, comment='Dirección de correo electrónico'),
        sa.Column('provider', sa.String(length=50), nullable=True, comment='Proveedor: gmail, outlook, yahoo, disroot, generic'),
        sa.Column('imap_host', sa.String(length=255), nullable=True, comment='Host IMAP'),
        sa.Column('imap_port', sa.Integer(), nullable=True, comment='Puerto IMAP'),
        sa.Column('imap_use_ssl', sa.Boolean(), nullable=False, comment='Usar SSL/TLS para IMAP'),
        sa.Column('smtp_host', sa.String(length=255), nullable=True, comment='Host SMTP'),
        sa.Column('smtp_port', sa.Integer(), nullable=True, comment='Puerto SMTP'),
        sa.Column('smtp_use_tls', sa.Boolean(), nullable=False, comment='Usar STARTTLS para SMTP'),
        sa.Column('smtp_use_ssl', sa.Boolean(), nullable=False, comment='Usar SSL para SMTP (puerto 465)'),
        sa.Column('auth_type', sa.String(length=50), nullable=False, comment='Tipo de auth: password, oauth2, app_password'),
        sa.Column('username', sa.String(length=255), nullable=True, comment='Usuario IMAP/SMTP (puede ser diferente al email)'),
        sa.Column('encrypted_password', sa.Text(), nullable=True, comment='Contraseña o App Password cifrada con pgcrypto'),
        sa.Column('encrypted_access_token', sa.Text(), nullable=True, comment='OAuth2 access token cifrado'),
        sa.Column('encrypted_refresh_token', sa.Text(), nullable=True, comment='OAuth2 refresh token cifrado'),
        sa.Column('token_expires_at', sa.DateTime(timezone=True), nullable=True, comment='Expiración del access token'),
        sa.Column('oauth_scopes', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Scopes OAuth2 concedidos'),
        sa.Column('is_active', sa.Boolean(), nullable=False, comment='Cuenta activa para sincronización'),
        sa.Column('is_default', sa.Boolean(), nullable=False, comment='Cuenta por defecto para enviar'),
        sa.Column('sync_enabled', sa.Boolean(), nullable=False, comment='Sincronización automática habilitada'),
        sa.Column('sync_interval_minutes', sa.Integer(), nullable=False, comment='Intervalo de sincronización en minutos'),
        sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True, comment='Última sincronización exitosa'),
        sa.Column('last_sync_error', sa.Text(), nullable=True, comment='Error de la última sincronización'),
        sa.Column('synced_folders', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=True, comment='Lista de carpetas a sincronizar'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('account_id', 'email_address', name='_account_email_uc'),
    )
    op.create_index('ix_email_accounts_account_id', 'email_accounts', ['account_id'], unique=False)
    op.create_index('ix_email_accounts_email_address', 'email_accounts', ['email_address'], unique=False)

    op.create_table(
        'email_folders',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('email_account_id', sa.UUID(), nullable=False),
        sa.Column('imap_name', sa.String(length=255), nullable=False, comment="Nombre real en IMAP (ej. 'INBOX', '[Gmail]/Sent Mail')"),
        sa.Column('display_name', sa.String(length=255), nullable=False, comment='Nombre para mostrar en UI'),
        sa.Column('folder_type', sa.String(length=50), nullable=True, comment='Tipo: inbox, sent, drafts, spam, trash, archive, custom'),
        sa.Column('is_subscribed', sa.Boolean(), nullable=False, comment='Suscrita en IMAP'),
        sa.Column('is_selectable', sa.Boolean(), nullable=False, comment='Se puede seleccionar (no es solo contenedor)'),
        sa.Column('message_count', sa.Integer(), nullable=False, comment='Número de mensajes'),
        sa.Column('unseen_count', sa.Integer(), nullable=False, comment='Número de mensajes no leídos'),
        sa.Column('parent_id', sa.UUID(), nullable=True),
        sa.Column('delimiter', sa.String(length=10), nullable=True, comment="Delimitador IMAP (ej. '/', '.')"),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.ForeignKeyConstraint(['email_account_id'], ['email_accounts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_id'], ['email_folders.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email_account_id', 'imap_name', name='_account_folder_imap_name_uc'),
    )
    op.create_index('ix_email_folders_account_id', 'email_folders', ['email_account_id'], unique=False)
    op.create_index(op.f('ix_email_folders_email_account_id'), 'email_folders', ['email_account_id'], unique=False)
    op.create_index(op.f('ix_email_folders_parent_id'), 'email_folders', ['parent_id'], unique=False)

    op.create_table(
        'emails',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('email_account_id', sa.UUID(), nullable=False),
        sa.Column('folder_id', sa.UUID(), nullable=True),
        sa.Column('imap_uid', sa.String(length=255), nullable=False, comment='UID IMAP del mensaje'),
        sa.Column('message_id', sa.String(length=512), nullable=True, comment='Message-ID header (global unique)'),
        sa.Column('in_reply_to', sa.String(length=512), nullable=True, comment='In-Reply-To header para threading'),
        sa.Column('references', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='References header como array para threading'),
        sa.Column('subject', sa.Text(), nullable=True, comment='Asunto del correo'),
        sa.Column('from_address', sa.String(length=512), nullable=True, comment='Remitente (From header)'),
        sa.Column('from_name', sa.String(length=255), nullable=True, comment='Nombre del remitente'),
        sa.Column('to_addresses', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Destinatarios To como array de {email, name}'),
        sa.Column('cc_addresses', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Destinatarios CC como array'),
        sa.Column('bcc_addresses', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Destinatarios BCC como array (solo salientes)'),
        sa.Column('reply_to', sa.String(length=512), nullable=True, comment='Reply-To header'),
        sa.Column('date_sent', sa.DateTime(timezone=True), nullable=True, comment='Fecha del header Date'),
        sa.Column('date_received', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True, comment='Fecha de recepción en nuestro sistema'),
        sa.Column('body_text', sa.Text(), nullable=True, comment='Cuerpo en texto plano'),
        sa.Column('body_html', sa.Text(), nullable=True, comment='Cuerpo en HTML'),
        sa.Column('snippet', sa.Text(), nullable=True, comment='Vista previa corta para lista'),
        sa.Column('is_read', sa.Boolean(), nullable=False, comment='Marcado como leído'),
        sa.Column('is_flagged', sa.Boolean(), nullable=False, comment='Marcado con bandera/estrella'),
        sa.Column('is_answered', sa.Boolean(), nullable=False, comment='Respondido'),
        sa.Column('is_draft', sa.Boolean(), nullable=False, comment='Es borrador'),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, comment='Marcado para eliminación (IMAP \\Deleted)'),
        sa.Column('is_spam', sa.Boolean(), nullable=False, comment='Marcado como spam'),
        sa.Column('has_attachments', sa.Boolean(), nullable=False, comment='Tiene adjuntos'),
        sa.Column('attachment_count', sa.Integer(), nullable=False, comment='Número de adjuntos'),
        sa.Column('total_attachment_size', sa.Integer(), nullable=False, comment='Tamaño total adjuntos en bytes'),
        sa.Column('thread_id', sa.String(length=512), nullable=True, comment='ID de hilo para agrupación'),
        sa.Column('size_bytes', sa.Integer(), nullable=True, comment='Tamaño del mensaje en bytes'),
        sa.Column('headers', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Cabeceras completas como JSON'),
        sa.Column('labels', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Labels/Gmail categories (Promotions, Social, etc.)'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.ForeignKeyConstraint(['email_account_id'], ['email_accounts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['folder_id'], ['email_folders.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email_account_id', 'imap_uid', name='_account_imap_uid_uc'),
    )
    op.create_index('ix_emails_account_folder', 'emails', ['email_account_id', 'folder_id'], unique=False)
    op.create_index(op.f('ix_emails_date_received'), 'emails', ['date_received'], unique=False)
    op.create_index('ix_emails_date_sent', 'emails', ['date_sent'], unique=False)
    op.create_index(op.f('ix_emails_email_account_id'), 'emails', ['email_account_id'], unique=False)
    op.create_index(op.f('ix_emails_folder_id'), 'emails', ['folder_id'], unique=False)
    op.create_index(op.f('ix_emails_imap_uid'), 'emails', ['imap_uid'], unique=False)
    op.create_index(op.f('ix_emails_in_reply_to'), 'emails', ['in_reply_to'], unique=False)
    op.create_index('ix_emails_is_read', 'emails', ['is_read'], unique=False)
    op.create_index(op.f('ix_emails_message_id'), 'emails', ['message_id'], unique=False)
    op.create_index(op.f('ix_emails_thread_id'), 'emails', ['thread_id'], unique=False)

    op.create_table(
        'email_attachments',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('email_id', sa.UUID(), nullable=False),
        sa.Column('filename', sa.String(length=512), nullable=True, comment='Nombre del archivo'),
        sa.Column('content_type', sa.String(length=255), nullable=True, comment='MIME type (ej. application/pdf)'),
        sa.Column('content_id', sa.String(length=512), nullable=True, comment='Content-ID para inline images (cid:)'),
        sa.Column('content_disposition', sa.String(length=50), nullable=True, comment='attachment o inline'),
        sa.Column('size_bytes', sa.Integer(), nullable=True, comment='Tamaño en bytes'),
        sa.Column('storage_path', sa.String(length=1024), nullable=True, comment='Ruta local o S3 donde se guarda el archivo'),
        sa.Column('is_inline', sa.Boolean(), nullable=False, comment='Es imagen inline (cid:)'),
        sa.Column('content_hash', sa.String(length=64), nullable=True, comment='SHA256 del contenido'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.ForeignKeyConstraint(['email_id'], ['emails.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_email_attachments_content_hash', 'email_attachments', ['content_hash'], unique=False)
    op.create_index('ix_email_attachments_email_id', 'email_attachments', ['email_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_email_attachments_email_id', table_name='email_attachments')
    op.drop_index('ix_email_attachments_content_hash', table_name='email_attachments')
    op.drop_table('email_attachments')

    op.drop_index(op.f('ix_emails_thread_id'), table_name='emails')
    op.drop_index(op.f('ix_emails_message_id'), table_name='emails')
    op.drop_index('ix_emails_is_read', table_name='emails')
    op.drop_index(op.f('ix_emails_in_reply_to'), table_name='emails')
    op.drop_index(op.f('ix_emails_imap_uid'), table_name='emails')
    op.drop_index(op.f('ix_emails_folder_id'), table_name='emails')
    op.drop_index(op.f('ix_emails_email_account_id'), table_name='emails')
    op.drop_index('ix_emails_date_sent', table_name='emails')
    op.drop_index(op.f('ix_emails_date_received'), table_name='emails')
    op.drop_index('ix_emails_account_folder', table_name='emails')
    op.drop_table('emails')

    op.drop_index(op.f('ix_email_folders_parent_id'), table_name='email_folders')
    op.drop_index(op.f('ix_email_folders_email_account_id'), table_name='email_folders')
    op.drop_index('ix_email_folders_account_id', table_name='email_folders')
    op.drop_table('email_folders')

    op.drop_index('ix_email_accounts_email_address', table_name='email_accounts')
    op.drop_index('ix_email_accounts_account_id', table_name='email_accounts')
    op.drop_table('email_accounts')
