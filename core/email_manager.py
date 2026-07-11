"""
Gestor de lógica de negocio para el módulo de correo electrónico.
"""

import imaplib
import smtplib
import email
from email.header import decode_header, make_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
import re
import uuid
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select, update, delete, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.database import (
    EmailAccount,
    EmailFolder,
    Email,
    EmailAttachment,
    Account,
)
from utils.db_session import DBSession
from utils.email_security import EmailSecurity, mask_secret, EmailSecurityError

logger = logging.getLogger(__name__)


def _to_uuid(val: Any) -> Any:
    if val is None:
        return None
    if isinstance(val, uuid.UUID):
        return val
    return uuid.UUID(val)


class EmailManager:
    """
    Gestiona la lógica de negocio del módulo de correo electrónico.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.security = EmailSecurity()

    @staticmethod
    def _decode_mime_header(raw: Optional[str]) -> Optional[str]:
        if not raw:
            return None
        try:
            return str(make_header(decode_header(raw)))
        except Exception:
            return raw

    @staticmethod
    def _normalize_email_address(raw: Optional[str]) -> Optional[str]:
        if not raw:
            return None
        addr = raw.strip()
        if "<" in addr and ">" in addr:
            addr = addr.split("<")[-1].split(">")[0]
        return addr.strip().lower()
    async def add_email_account(
        self,
        account_id: str,
        name: str,
        email_address: str,
        provider: Optional[str] = None,
        imap_host: Optional[str] = None,
        imap_port: int = 993,
        imap_use_ssl: bool = True,
        smtp_host: Optional[str] = None,
        smtp_port: int = 587,
        smtp_use_tls: bool = True,
        smtp_use_ssl: bool = False,
        auth_type: str = "password",
        username: Optional[str] = None,
        password: Optional[str] = None,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        token_expires_at: Optional[datetime] = None,
        oauth_scopes: Optional[List[str]] = None,
        is_default: bool = False,
        sync_enabled: bool = True,
        sync_interval_minutes: int = 15,
    ) -> Dict[str, Any]:
        account_uuid = _to_uuid(account_id)
        if not account_uuid:
            raise EmailSecurityError("account_id inválido.")

        account = await self.db.get(Account, account_uuid)
        if not account:
            raise EmailSecurityError("La cuenta no existe.")

        if is_default:
            await self.db.execute(
                update(EmailAccount)
                .where(EmailAccount.account_id == account_uuid)
                .values(is_default=False)
            )

        encrypted_password = self.security.encrypt(password or "")
        encrypted_access = self.security.encrypt(access_token or "")
        encrypted_refresh = self.security.encrypt(refresh_token or "")

        new_account = EmailAccount(
            account_id=account_uuid,
            name=name.strip(),
            email_address=email_address.strip().lower(),
            provider=provider,
            imap_host=imap_host,
            imap_port=imap_port,
            imap_use_ssl=imap_use_ssl,
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            smtp_use_tls=smtp_use_tls,
            smtp_use_ssl=smtp_use_ssl,
            auth_type=auth_type,
            username=username.strip() if username else None,
            encrypted_password=encrypted_password,
            encrypted_access_token=encrypted_access,
            encrypted_refresh_token=encrypted_refresh,
            token_expires_at=token_expires_at,
            oauth_scopes=oauth_scopes,
            is_default=is_default,
            sync_enabled=sync_enabled,
            sync_interval_minutes=sync_interval_minutes,
        )
        self.db.add(new_account)
        await self.db.commit()
        await self.db.refresh(new_account)

        logger.info("Cuenta de correo creada: %s", mask_secret(email_address))
        return {
            "id": str(new_account.id),
            "name": new_account.name,
            "email_address": new_account.email_address,
            "provider": new_account.provider,
            "is_default": new_account.is_default,
            "sync_enabled": new_account.sync_enabled,
        }

    async def get_email_account(self, account_id: str, email_account_id: str) -> Dict[str, Any]:
        acc_uuid = _to_uuid(account_id)
        ea_uuid = _to_uuid(email_account_id)
        stmt = select(EmailAccount).where(
            EmailAccount.id == ea_uuid,
            EmailAccount.account_id == acc_uuid,
        )
        result = await self.db.execute(stmt)
        account = result.scalar_one_or_none()
        if not account:
            raise EmailSecurityError("Cuenta de correo no encontrada.")

        return {
            "id": str(account.id),
            "name": account.name,
            "email_address": account.email_address,
            "provider": account.provider,
            "auth_type": account.auth_type,
            "imap_host": account.imap_host,
            "imap_port": account.imap_port,
            "imap_use_ssl": account.imap_use_ssl,
            "smtp_host": account.smtp_host,
            "smtp_port": account.smtp_port,
            "smtp_use_tls": account.smtp_use_tls,
            "smtp_use_ssl": account.smtp_use_ssl,
            "username": account.username,
            "password": self.security.decrypt(account.encrypted_password),
            "access_token": self.security.decrypt(account.encrypted_access_token),
            "refresh_token": self.security.decrypt(account.encrypted_refresh_token),
            "token_expires_at": account.token_expires_at.isoformat() if account.token_expires_at else None,
            "is_active": account.is_active,
            "is_default": account.is_default,
            "sync_enabled": account.sync_enabled,
            "last_sync_at": account.last_sync_at.isoformat() if account.last_sync_at else None,
            "last_sync_error": account.last_sync_error,
        }

    async def list_email_accounts(self, account_id: str) -> List[Dict[str, Any]]:
        acc_uuid = _to_uuid(account_id)
        stmt = (
            select(EmailAccount)
            .where(EmailAccount.account_id == acc_uuid)
            .order_by(EmailAccount.created_at.desc())
        )
        result = await self.db.execute(stmt)
        accounts = result.scalars().all()

        return [
            {
                "id": str(a.id),
                "name": a.name,
                "email_address": a.email_address,
                "provider": a.provider,
                "auth_type": a.auth_type,
                "is_active": a.is_active,
                "is_default": a.is_default,
                "sync_enabled": a.sync_enabled,
                "last_sync_at": a.last_sync_at.isoformat() if a.last_sync_at else None,
                "last_sync_error": a.last_sync_error,
            }
            for a in accounts
        ]

    async def delete_email_account(self, account_id: str, email_account_id: str) -> None:
        acc_uuid = _to_uuid(account_id)
        ea_uuid = _to_uuid(email_account_id)
        stmt = (
            delete(EmailAccount)
            .where(EmailAccount.id == ea_uuid, EmailAccount.account_id == acc_uuid)
        )
        await self.db.execute(stmt)
        await self.db.commit()

    async def update_email_account(
        self,
        account_id: str,
        email_account_id: str,
        **fields: Any,
    ) -> Dict[str, Any]:
        acc_uuid = _to_uuid(account_id)
        ea_uuid = _to_uuid(email_account_id)
        stmt = select(EmailAccount).where(
            EmailAccount.id == ea_uuid,
            EmailAccount.account_id == acc_uuid,
        )
        result = await self.db.execute(stmt)
        account = result.scalar_one_or_none()
        if not account:
            raise EmailSecurityError("Cuenta de correo no encontrada.")

        password = fields.pop("password", None)
        if password is not None:
            fields["encrypted_password"] = self.security.encrypt(password)

        access_token = fields.pop("access_token", None)
        if access_token is not None:
            fields["encrypted_access_token"] = self.security.encrypt(access_token)

        refresh_token = fields.pop("refresh_token", None)
        if refresh_token is not None:
            fields["encrypted_refresh_token"] = self.security.encrypt(refresh_token)

        token_expires_at = fields.pop("token_expires_at", None)
        if token_expires_at is not None and isinstance(token_expires_at, str):
            fields["token_expires_at"] = datetime.fromisoformat(token_expires_at)

        if fields.get("is_default"):
            await self.db.execute(
                update(EmailAccount)
                .where(EmailAccount.account_id == acc_uuid)
                .values(is_default=False)
            )

        await self.db.execute(
            update(EmailAccount)
            .where(EmailAccount.id == ea_uuid)
            .values(**fields)
        )
        await self.db.commit()
        return {"updated": True, "email_account_id": email_account_id}

    async def test_imap_connection(self, account_id: str, email_account_id: str) -> Dict[str, Any]:
        data = await self.get_email_account(account_id, email_account_id)
        try:
            if data["imap_use_ssl"]:
                conn = imaplib.IMAP4_SSL(data["imap_host"], data["imap_port"])
            else:
                conn = imaplib.IMAP4(data["imap_host"], data["imap_port"])

            if data["auth_type"] == "oauth2" and data["access_token"]:
                auth_string = f'user="{data["username"]}"\x01auth=Bearer {data["access_token"]}\x01\x01'
                conn.authenticate("XOAUTH2", lambda x: auth_string)
            else:
                conn.login(data["username"], data["password"])

            status, folders = conn.list()
            conn.logout()
            return {
                "ok": True,
                "message": "Conexión IMAP exitosa.",
                "folders_count": len(folders) if folders else 0,
            }
        except Exception as exc:
            logger.error("Error IMAP para %s: %s", mask_secret(data["email_address"]), exc)
            return {
                "ok": False,
                "message": f"Error de conexión IMAP: {exc}",
            }

    async def test_smtp_connection(self, account_id: str, email_account_id: str) -> Dict[str, Any]:
        data = await self.get_email_account(account_id, email_account_id)
        try:
            if data["smtp_use_ssl"]:
                conn = smtplib.SMTP_SSL(data["smtp_host"], data["smtp_port"])
            else:
                conn = smtplib.SMTP(data["smtp_host"], data["smtp_port"])
                if data["smtp_use_tls"]:
                    conn.starttls()

            conn.login(data["username"], data["password"])
            conn.noop()
            conn.quit()
            return {
                "ok": True,
                "message": "Conexión SMTP exitosa.",
            }
        except Exception as exc:
            logger.error("Error SMTP para %s: %s", mask_secret(data["email_address"]), exc)
            return {
                "ok": False,
                "message": f"Error de conexión SMTP: {exc}",
            }

    async def sync_folders(self, account_id: str, email_account_id: str) -> List[Dict[str, Any]]:
        data = await self.get_email_account(account_id, email_account_id)
        imap_host = data["imap_host"]
        imap_port = data["imap_port"]
        imap_use_ssl = data["imap_use_ssl"]
        username = data["username"]
        password = data["password"]
        access_token = data.get("access_token")
        auth_type = data.get("auth_type", "password")

        if imap_use_ssl:
            conn = imaplib.IMAP4_SSL(imap_host, imap_port)
        else:
            conn = imaplib.IMAP4(imap_host, imap_port)

        if auth_type == "oauth2" and access_token:
            auth_string = f'user="{username}"\x01auth=Bearer {access_token}\x01\x01'
            conn.authenticate("XOAUTH2", lambda x: auth_string)
        else:
            conn.login(username, password)

        status, list_data = conn.list()
        if status != "OK":
            conn.logout()
            raise EmailSecurityError("No se pudo listar carpetas IMAP.")

        folders: List[Dict[str, Any]] = []
        ea_uuid = _to_uuid(email_account_id)

        for line in list_data:
            if not line:
                continue
            try:
                decoded = line.decode("utf-8", errors="replace")
            except Exception:
                continue
            match = re.search(r'"([^"]+)"\s+"([^"]+)"$', decoded)
            if not match:
                parts = decoded.split()
                if len(parts) >= 3:
                    imap_name = " ".join(parts[2:]).strip('"')
                else:
                    continue
            else:
                imap_name = match.group(2)

            imap_name = imap_name.strip()
            if not imap_name:
                continue

            display_name = imap_name
            folder_type = "custom"
            lower = imap_name.lower()
            if lower == "inbox":
                display_name = "Inbox"
                folder_type = "inbox"
            elif lower in {"sent", "sent mail"}:
                display_name = "Sent"
                folder_type = "sent"
            elif lower in {"drafts", "draft"}:
                display_name = "Drafts"
                folder_type = "drafts"
            elif lower in {"spam", "junk"}:
                display_name = "Spam"
                folder_type = "spam"
            elif lower in {"trash", "bin"}:
                display_name = "Trash"
                folder_type = "trash"
            elif lower in {"archive", "archived"}:
                display_name = "Archive"
                folder_type = "archive"

            stmt = select(EmailFolder).where(
                EmailFolder.email_account_id == ea_uuid,
                EmailFolder.imap_name == imap_name,
            )
            existing = (await self.db.execute(stmt)).scalar_one_or_none()

            if existing:
                existing.display_name = display_name
                existing.folder_type = folder_type
            else:
                new_folder = EmailFolder(
                    email_account_id=ea_uuid,
                    imap_name=imap_name,
                    display_name=display_name,
                    folder_type=folder_type,
                )
                self.db.add(new_folder)

            folders.append({"imap_name": imap_name, "display_name": display_name, "folder_type": folder_type})

        await self.db.commit()

        for folder_name in ["INBOX"] + [f["imap_name"] for f in folders if f["imap_name"].upper() != "INBOX"]:
            try:
                conn.select(folder_name, readonly=True)
                status, data_resp = conn.status(folder_name, "(MESSAGES UNSEEN)")
                if status == "OK" and data_resp and data_resp[0]:
                    parts = data_resp[0].split()
                    message_count = int(parts[1]) if len(parts) > 1 else 0
                    unseen_count = int(parts[3]) if len(parts) > 3 else 0
                    stmt = (
                        update(EmailFolder)
                        .where(
                            EmailFolder.email_account_id == ea_uuid,
                            EmailFolder.imap_name == folder_name,
                        )
                        .values(message_count=message_count, unseen_count=unseen_count)
                    )
                    await self.db.execute(stmt)
            except Exception:
                continue

        await self.db.commit()
        conn.logout()
        return folders
    async def list_folders(self, account_id: str, email_account_id: str) -> List[Dict[str, Any]]:
        ea_uuid = _to_uuid(email_account_id)
        acc_uuid = _to_uuid(account_id)
        stmt = (
            select(EmailFolder)
            .where(EmailFolder.email_account_id == ea_uuid)
            .order_by(EmailFolder.folder_type.nulls_last(), EmailFolder.display_name)
        )
        result = await self.db.execute(stmt)
        folders = result.scalars().all()
        return [
            {
                "id": str(f.id),
                "imap_name": f.imap_name,
                "display_name": f.display_name,
                "folder_type": f.folder_type,
                "message_count": f.message_count,
                "unseen_count": f.unseen_count,
            }
            for f in folders
        ]

    async def sync_emails_for_folder(
        self,
        account_id: str,
        email_account_id: str,
        folder_id: str,
        limit: int = 100,
    ) -> Dict[str, Any]:
        data = await self.get_email_account(account_id, email_account_id)
        folder_uuid = _to_uuid(folder_id)
        stmt = select(EmailFolder).where(EmailFolder.id == folder_uuid)
        folder = (await self.db.execute(stmt)).scalar_one_or_none()
        if not folder:
            raise EmailSecurityError("Carpeta no encontrada.")

        imap_host = data["imap_host"]
        imap_port = data["imap_port"]
        imap_use_ssl = data["imap_use_ssl"]
        username = data["username"]
        password = data["password"]
        access_token = data.get("access_token")
        auth_type = data.get("auth_type", "password")

        if imap_use_ssl:
            conn = imaplib.IMAP4_SSL(imap_host, imap_port)
        else:
            conn = imaplib.IMAP4(imap_host, imap_port)

        if auth_type == "oauth2" and access_token:
            auth_string = f'user="{username}"\x01auth=Bearer {access_token}\x01\x01'
            conn.authenticate("XOAUTH2", lambda x: auth_string)
        else:
            conn.login(username, password)

        conn.select(folder.imap_name, readonly=False)
        status, data_resp = conn.uid("search", None, "ALL")
        if status != "OK":
            conn.logout()
            raise EmailSecurityError("No se pudo buscar mensajes en IMAP.")

        uid_list = data_resp[0].split() if data_resp and data_resp[0] else []
        uid_list = uid_list[-limit:] if limit and len(uid_list) > limit else uid_list

        fetched = 0
        for uid in uid_list:
            try:
                status, msg_data = conn.uid("fetch", uid, "(RFC822)")
                if status != "OK" or not msg_data or msg_data[0] is None:
                    continue
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)
                await self._store_message(
                    account_id=account_id,
                    email_account_id=email_account_id,
                    folder_id=str(folder.id),
                    imap_uid=uid.decode("utf-8", errors="replace"),
                    msg=msg,
                    raw_bytes=raw_email,
                )
                fetched += 1
            except Exception as exc:
                logger.warning("Error procesando mensaje IMAP uid=%s: %s", uid, exc)
                continue

        await self.db.commit()
        conn.logout()
        return {"fetched": fetched, "folder_id": folder_id}

    async def _store_message(
        self,
        account_id: str,
        email_account_id: str,
        folder_id: str,
        imap_uid: str,
        msg: email.message.Message,
        raw_bytes: bytes,
    ) -> Optional[Email]:
        ea_uuid = _to_uuid(email_account_id)
        folder_uuid = _to_uuid(folder_id)
        acc_uuid = _to_uuid(account_id)

        message_id = self._decode_mime_header(msg.get("Message-ID"))
        in_reply_to = self._decode_mime_header(msg.get("In-Reply-To"))
        subject = self._decode_mime_header(msg.get("Subject"))
        from_raw = self._decode_mime_header(msg.get("From"))
        to_raw = self._decode_mime_header(msg.get("To"))
        cc_raw = self._decode_mime_header(msg.get("CC"))
        reply_to = self._decode_mime_header(msg.get("Reply-To"))
        date_sent_raw = msg.get("Date")

        from_address = self._normalize_email_address(from_raw)
        to_addresses = self._parse_addresses(to_raw)
        cc_addresses = self._parse_addresses(cc_raw)

        date_sent = None
        if date_sent_raw:
            try:
                parsed = email.utils.parsedate_to_datetime(date_sent_raw)
                date_sent = parsed.astimezone(timezone.utc).replace(tzinfo=None)
            except Exception:
                date_sent = None

        body_text, body_html, snippet = self._extract_body(msg)

        stmt = select(Email).where(
            Email.email_account_id == ea_uuid,
            Email.imap_uid == imap_uid,
        )
        existing = (await self.db.execute(stmt)).scalar_one_or_none()
        if existing:
            existing.subject = subject
            existing.from_address = from_address
            existing.to_addresses = to_addresses
            existing.cc_addresses = cc_addresses
            existing.reply_to = reply_to
            existing.date_sent = date_sent
            existing.body_text = body_text
            existing.body_html = body_html
            existing.snippet = snippet
            existing.headers = dict(msg.items())
            return existing

        new_email = Email(
            email_account_id=ea_uuid,
            folder_id=folder_uuid,
            imap_uid=imap_uid,
            message_id=message_id,
            in_reply_to=in_reply_to,
            subject=subject,
            from_address=from_address,
            from_name=from_raw,
            to_addresses=to_addresses,
            cc_addresses=cc_addresses,
            reply_to=reply_to,
            date_sent=date_sent,
            body_text=body_text,
            body_html=body_html,
            snippet=snippet,
            size_bytes=len(raw_bytes),
            headers=dict(msg.items()),
        )
        self.db.add(new_email)
        await self.db.flush()
        return new_email

    @staticmethod
    def _parse_addresses(raw: Optional[str]) -> Optional[List[Dict[str, Optional[str]]]]:
        if not raw:
            return None
        addresses = email.utils.getaddresses([raw])
        result = []
        for name, addr in addresses:
            result.append({"name": name or None, "email": addr.lower() if addr else None})
        return result or None

    @staticmethod
    def _extract_body(msg: email.message.Message) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        body_text: Optional[str] = None
        body_html: Optional[str] = None
        snippet: Optional[str] = None

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                disposition = str(part.get("Content-Disposition") or "")
                if "attachment" in disposition:
                    continue
                payload = part.get_payload(decode=True)
                if payload is None:
                    continue
                charset = part.get_content_charset() or "utf-8"
                try:
                    text = payload.decode(charset, errors="replace")
                except Exception:
                    text = payload.decode("utf-8", errors="replace")
                if content_type == "text/plain" and body_text is None:
                    body_text = text
                elif content_type == "text/html" and body_html is None:
                    body_html = text
        else:
            payload = msg.get_payload(decode=True)
            if payload is not None:
                charset = msg.get_content_charset() or "utf-8"
                try:
                    text = payload.decode(charset, errors="replace")
                except Exception:
                    text = payload.decode("utf-8", errors="replace")
                if msg.get_content_type() == "text/html":
                    body_html = text
                else:
                    body_text = text

        if body_text:
            snippet = body_text[:300].replace("\n", " ").strip()
        elif body_html:
            text_only = re.sub(r"<[^>]+>", " ", body_html)
            text_only = re.sub(r"\s+", " ", text_only).strip()
            snippet = text_only[:300]
        return body_text, body_html, snippet

    async def list_emails(
        self,
        account_id: str,
        email_account_id: str,
        folder_id: Optional[str] = None,
        is_read: Optional[bool] = None,
        is_flagged: Optional[bool] = None,
        is_spam: Optional[bool] = None,
        is_deleted: Optional[bool] = None,
        is_draft: Optional[bool] = None,
        search_term: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        ea_uuid = _to_uuid(email_account_id)
        acc_uuid = _to_uuid(account_id)
        stmt = (
            select(Email)
            .options(selectinload(Email.attachments))
            .where(Email.email_account_id == ea_uuid)
        )

        if folder_id:
            folder_uuid = _to_uuid(folder_id)
            stmt = stmt.where(Email.folder_id == folder_uuid)
        if is_read is not None:
            stmt = stmt.where(Email.is_read == is_read)
        if is_flagged is not None:
            stmt = stmt.where(Email.is_flagged == is_flagged)
        if is_spam is not None:
            stmt = stmt.where(Email.is_spam == is_spam)
        if is_deleted is not None:
            stmt = stmt.where(Email.is_deleted == is_deleted)
        if is_draft is not None:
            stmt = stmt.where(Email.is_draft == is_draft)
        if search_term:
            term = f"%{search_term}%"
            stmt = stmt.where(
                or_(
                    Email.subject.ilike(term),
                    Email.from_address.ilike(term),
                    Email.body_text.ilike(term),
                )
            )

        total_stmt = select(func.count(Email.id)).where(stmt.whereclause)
        total = (await self.db.execute(total_stmt)).scalar_one() or 0

        stmt = stmt.order_by(Email.date_sent.desc().nullslast(), Email.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        emails = result.scalars().all()

        items = []
        for e in emails:
            items.append(
                {
                    "id": str(e.id),
                    "folder_id": str(e.folder_id) if e.folder_id else None,
                    "subject": e.subject,
                    "from_address": e.from_address,
                    "from_name": e.from_name,
                    "to_addresses": e.to_addresses,
                    "date_sent": e.date_sent.isoformat() if e.date_sent else None,
                    "date_received": e.date_received.isoformat() if e.date_received else None,
                    "snippet": e.snippet,
                    "is_read": e.is_read,
                    "is_flagged": e.is_flagged,
                    "is_deleted": e.is_deleted,
                    "is_draft": e.is_draft,
                    "is_spam": e.is_spam,
                    "has_attachments": e.has_attachments,
                    "attachment_count": e.attachment_count,
                    "message_id": e.message_id,
                    "thread_id": e.thread_id,
                    "attachments": [
                        {
                            "id": str(a.id),
                            "filename": a.filename,
                            "content_type": a.content_type,
                            "size_bytes": a.size_bytes,
                            "is_inline": a.is_inline,
                        }
                        for a in e.attachments
                    ],
                }
            )
        return total, items

    async def get_email(self, account_id: str, email_id: str) -> Dict[str, Any]:
        acc_uuid = _to_uuid(account_id)
        email_uuid = _to_uuid(email_id)
        stmt = (
            select(Email)
            .options(selectinload(Email.attachments))
            .where(Email.id == email_uuid)
        )
        result = await self.db.execute(stmt)
        e = result.scalar_one_or_none()
        if not e:
            raise EmailSecurityError("Correo no encontrado.")

        if e.email_account.account_id != acc_uuid:
            raise EmailSecurityError("No tiene acceso a este correo.")

        return {
            "id": str(e.id),
            "folder_id": str(e.folder_id) if e.folder_id else None,
            "subject": e.subject,
            "from_address": e.from_address,
            "from_name": e.from_name,
            "to_addresses": e.to_addresses,
            "cc_addresses": e.cc_addresses,
            "reply_to": e.reply_to,
            "date_sent": e.date_sent.isoformat() if e.date_sent else None,
            "date_received": e.date_received.isoformat() if e.date_received else None,
            "body_text": e.body_text,
            "body_html": e.body_html,
            "snippet": e.snippet,
            "is_read": e.is_read,
            "is_flagged": e.is_flagged,
            "is_deleted": e.is_deleted,
            "is_draft": e.is_draft,
            "is_spam": e.is_spam,
            "has_attachments": e.has_attachments,
            "attachment_count": e.attachment_count,
            "message_id": e.message_id,
            "in_reply_to": e.in_reply_to,
            "references": e.references,
            "thread_id": e.thread_id,
            "headers": e.headers,
            "attachments": [
                {
                    "id": str(a.id),
                    "filename": a.filename,
                    "content_type": a.content_type,
                    "content_id": a.content_id,
                    "content_disposition": a.content_disposition,
                    "size_bytes": a.size_bytes,
                    "storage_path": a.storage_path,
                    "is_inline": a.is_inline,
                }
                for a in e.attachments
            ],
        }

    async def update_email_flags(
        self,
        account_id: str,
        email_id: str,
        is_read: Optional[bool] = None,
        is_flagged: Optional[bool] = None,
        is_deleted: Optional[bool] = None,
        is_spam: Optional[bool] = None,
        folder_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        acc_uuid = _to_uuid(account_id)
        email_uuid = _to_uuid(email_id)
        stmt = select(Email).where(Email.id == email_uuid)
        result = await self.db.execute(stmt)
        e = result.scalar_one_or_none()
        if not e:
            raise EmailSecurityError("Correo no encontrado.")
        if e.email_account.account_id != acc_uuid:
            raise EmailSecurityError("No tiene acceso a este correo.")

        values: Dict[str, Any] = {}
        if is_read is not None:
            values["is_read"] = is_read
        if is_flagged is not None:
            values["is_flagged"] = is_flagged
        if is_deleted is not None:
            values["is_deleted"] = is_deleted
        if is_spam is not None:
            values["is_spam"] = is_spam
        if folder_id is not None:
            values["folder_id"] = _to_uuid(folder_id)

        if values:
            await self.db.execute(update(Email).where(Email.id == email_uuid).values(**values))
            await self.db.commit()

        return {"updated": True, "email_id": email_id}

    async def delete_email(self, account_id: str, email_id: str) -> None:
        acc_uuid = _to_uuid(account_id)
        email_uuid = _to_uuid(email_id)
        stmt = select(Email).where(Email.id == email_uuid)
        result = await self.db.execute(stmt)
        e = result.scalar_one_or_none()
        if not e:
            raise EmailSecurityError("Correo no encontrado.")
        if e.email_account.account_id != acc_uuid:
            raise EmailSecurityError("No tiene acceso a este correo.")

        await self.db.delete(e)
        await self.db.commit()
    async def send_email(
        self,
        account_id: str,
        email_account_id: str,
        to_addresses: List[str],
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        cc_addresses: Optional[List[str]] = None,
        bcc_addresses: Optional[List[str]] = None,
        attachments: Optional[List[str]] = None,
        reply_to_message_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        data = await self.get_email_account(account_id, email_account_id)
        username = data["username"]
        password = data["password"]
        from_address = data["email_address"]
        smtp_host = data["smtp_host"]
        smtp_port = data["smtp_port"]
        smtp_use_tls = data["smtp_use_tls"]
        smtp_use_ssl = data["smtp_use_ssl"]

        msg = MIMEMultipart()
        msg["From"] = from_address
        msg["To"] = ", ".join(to_addresses)
        msg["Subject"] = subject
        if cc_addresses:
            msg["Cc"] = ", ".join(cc_addresses)
        if reply_to_message_id:
            msg["In-Reply-To"] = reply_to_message_id
            msg["References"] = reply_to_message_id

        msg.attach(MIMEText(body_text or "", "plain", "utf-8"))
        if body_html:
            msg.attach(MIMEText(body_html, "html", "utf-8"))

        for file_path in attachments or []:
            if not os.path.exists(file_path):
                continue
            with open(file_path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                "attachment",
                filename=("utf-8", "", os.path.basename(file_path)),
            )
            msg.attach(part)

        all_recipients = list(to_addresses) + list(cc_addresses or []) + list(bcc_addresses or [])
        try:
            if smtp_use_ssl:
                conn = smtplib.SMTP_SSL(smtp_host, smtp_port)
            else:
                conn = smtplib.SMTP(smtp_host, smtp_port)
                if smtp_use_tls:
                    conn.starttls()

            conn.login(username, password)
            conn.sendmail(from_address, all_recipients, msg.as_string())
            conn.quit()
            return {
                "ok": True,
                "message": "Correo enviado correctamente.",
                "from": from_address,
                "to": to_addresses,
            }
        except Exception as exc:
            logger.error("Error enviando correo desde %s: %s", mask_secret(from_address), exc)
            return {
                "ok": False,
                "message": f"Error enviando correo: {exc}",
            }
    async def search_emails(
        self,
        account_id: str,
        email_account_id: str,
        query: str,
        folder_id: Optional[str] = None,
        is_read: Optional[bool] = None,
        is_flagged: Optional[bool] = None,
        is_spam: Optional[bool] = None,
        is_deleted: Optional[bool] = None,
        is_draft: Optional[bool] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        """
        Alias semántico de list_emails orientado a búsqueda por texto.
        """
        return await self.list_emails(
            account_id=account_id,
            email_account_id=email_account_id,
            folder_id=folder_id,
            is_read=is_read,
            is_flagged=is_flagged,
            is_spam=is_spam,
            is_deleted=is_deleted,
            is_draft=is_draft,
            search_term=query,
            skip=offset,
            limit=limit,
        )

    async def get_thread(
        self,
        account_id: str,
        email_account_id: str,
        thread_id: str,
    ) -> List[Dict[str, Any]]:
        ea_uuid = _to_uuid(email_account_id)
        acc_uuid = _to_uuid(account_id)
        stmt = (
            select(Email)
            .options(selectinload(Email.attachments))
            .where(Email.email_account_id == ea_uuid, Email.thread_id == thread_id)
            .order_by(Email.date_sent.asc().nullslast(), Email.created_at.asc())
        )
        result = await self.db.execute(stmt)
        emails = result.scalars().all()

        items = []
        for e in emails:
            if e.email_account.account_id != acc_uuid:
                continue
            items.append(
                {
                    "id": str(e.id),
                    "folder_id": str(e.folder_id) if e.folder_id else None,
                    "subject": e.subject,
                    "from_address": e.from_address,
                    "from_name": e.from_name,
                    "to_addresses": e.to_addresses,
                    "date_sent": e.date_sent.isoformat() if e.date_sent else None,
                    "date_received": e.date_received.isoformat() if e.date_received else None,
                    "snippet": e.snippet,
                    "is_read": e.is_read,
                    "is_flagged": e.is_flagged,
                    "is_deleted": e.is_deleted,
                    "is_draft": e.is_draft,
                    "is_spam": e.is_spam,
                    "has_attachments": e.has_attachments,
                    "attachment_count": e.attachment_count,
                    "message_id": e.message_id,
                    "in_reply_to": e.in_reply_to,
                    "references": e.references,
                    "thread_id": e.thread_id,
                    "attachments": [
                        {
                            "id": str(a.id),
                            "filename": a.filename,
                            "content_type": a.content_type,
                            "size_bytes": a.size_bytes,
                            "is_inline": a.is_inline,
                        }
                        for a in e.attachments
                    ],
                }
            )
        return items
