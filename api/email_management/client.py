import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
import base64
from typing import List, Dict, Any

def decode_mime_header(header_value: str) -> str:
    if not header_value:
        return ""
    try:
        decoded_parts = decode_header(header_value)
        header_text = ""
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                header_text += part.decode(encoding or "utf-8", errors="ignore")
            else:
                header_text += part
        return header_text
    except Exception:
        return str(header_value)

def generate_xoauth2_string(username: str, access_token: str) -> bytes:
    auth_string = f"user={username}\x01auth=Bearer {access_token}\x01\x01"
    return base64.b64encode(auth_string.encode('utf-8'))

class EmailClient:
    @staticmethod
    def get_imap_connection(config, password: str = None, access_token: str = None):
        if config.imap_ssl:
            client = imaplib.IMAP4_SSL(config.imap_server, config.imap_port)
        else:
            client = imaplib.IMAP4(config.imap_server, config.imap_port)
        
        if access_token:
            xauth = generate_xoauth2_string(config.imap_user, access_token)
            # authenticate XOAUTH2 expects a single parameter response callback
            # where we pass the generated base64 string
            client.authenticate('XOAUTH2', lambda x: xauth)
        else:
            client.login(config.imap_user, password)
        return client

    @staticmethod
    def get_smtp_connection(config, password: str = None, access_token: str = None):
        if config.smtp_ssl:
            server = smtplib.SMTP_SSL(config.smtp_server, config.smtp_port)
        else:
            server = smtplib.SMTP(config.smtp_server, config.smtp_port)
            server.starttls()
        
        if access_token:
            xauth = generate_xoauth2_string(config.smtp_user, access_token).decode('utf-8')
            # XOAUTH2 SMTP auth protocol uses client AUTH command
            server.docmd('AUTH', f'XOAUTH2 {xauth}')
        else:
            server.login(config.smtp_user, password)
        return server

    @classmethod
    def fetch_folders(cls, config, password: str = None, access_token: str = None) -> List[str]:
        client = cls.get_imap_connection(config, password, access_token)
        try:
            status, folders = client.list()
            result = []
            if status == 'OK':
                for f in folders:
                    parts = f.decode('utf-8').split(' "/" ')
                    if len(parts) > 1:
                        name = parts[1].strip('"')
                        result.append(name)
                    else:
                        # Fallback for other folder delimiters
                        parts = f.decode('utf-8').split(' ')
                        if len(parts) > 0:
                            result.append(parts[-1].strip('"'))
            return result
        finally:
            client.logout()

    @classmethod
    def fetch_messages(cls, config, password: str = None, folder: str = "INBOX", limit: int = 20, offset: int = 0, access_token: str = None) -> List[Dict[str, Any]]:
        client = cls.get_imap_connection(config, password, access_token)
        try:
            client.select(folder, readonly=True)
            status, messages = client.uid('search', None, 'ALL')
            if status != 'OK':
                return []
            uids = messages[0].split()
            uids = list(reversed(uids)) # Newest first
            slice_uids = uids[offset : offset + limit]
            
            result = []
            for uid in slice_uids:
                status, data = client.uid('fetch', uid, '(BODY[HEADER.FIELDS (SUBJECT FROM TO DATE)])')
                if status == 'OK' and data[0]:
                    msg = email.message_from_bytes(data[0][1])
                    subject = decode_mime_header(msg.get("Subject", "Sin Asunto"))
                    sender = decode_mime_header(msg.get("From", ""))
                    to = decode_mime_header(msg.get("To", ""))
                    date = decode_mime_header(msg.get("Date", ""))
                    result.append({
                        "uid": uid.decode('utf-8'),
                        "subject": subject,
                        "from": sender,
                        "to": to,
                        "date": date
                    })
            return result
        finally:
            client.logout()

    @classmethod
    def fetch_message_detail(cls, config, password: str = None, folder: str = "INBOX", uid: str = None, access_token: str = None) -> Dict[str, Any]:
        client = cls.get_imap_connection(config, password, access_token)
        try:
            client.select(folder, readonly=True)
            status, data = client.uid('fetch', uid.encode('utf-8'), '(RFC822)')
            if status != 'OK' or not data[0]:
                raise ValueError("Email not found")
            
            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)
            
            subject = decode_mime_header(msg.get("Subject", "Sin Asunto"))
            sender = decode_mime_header(msg.get("From", ""))
            to = decode_mime_header(msg.get("To", ""))
            date = decode_mime_header(msg.get("Date", ""))
            
            text_body = ""
            html_body = ""
            attachments = []
            
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))
                    
                    # Detect attachment
                    if "attachment" in content_disposition:
                        filename = part.get_filename()
                        if filename:
                            decoded_filename = decode_mime_header(filename)
                            attachments.append({
                                "filename": decoded_filename,
                                "content_type": content_type,
                                "size": len(part.get_payload(decode=True) or b'')
                            })
                    else:
                        if content_type == "text/plain":
                            payload = part.get_payload(decode=True)
                            text_body += payload.decode(part.get_content_charset() or 'utf-8', errors='ignore')
                        elif content_type == "text/html":
                            payload = part.get_payload(decode=True)
                            html_body += payload.decode(part.get_content_charset() or 'utf-8', errors='ignore')
            else:
                payload = msg.get_payload(decode=True)
                text_body = payload.decode(msg.get_content_charset() or 'utf-8', errors='ignore')
                if msg.get_content_type() == "text/html":
                    html_body = text_body

            return {
                "uid": uid,
                "subject": subject,
                "from": sender,
                "to": to,
                "date": date,
                "text": text_body,
                "html": html_body or f"<pre style='font-family: sans-serif; white-space: pre-wrap;'>{text_body}</pre>",
                "attachments": attachments
            }
        finally:
            client.logout()

    @classmethod
    def send_email(cls, config, password: str = None, to: str = "", cc: list = None, subject: str = "", body: str = "", access_token: str = None):
        server = cls.get_smtp_connection(config, password, access_token)
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = config.smtp_user
            msg['To'] = to
            if cc:
                msg['Cc'] = ", ".join(cc)
            
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            msg.attach(MIMEText(body.replace("\n", "<br>"), 'html', 'utf-8'))
            
            recipients = [to] + (cc or [])
            server.sendmail(config.smtp_user, recipients, msg.as_string())
        finally:
            server.quit()
