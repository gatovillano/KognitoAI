import os
import imaplib
import email
from email.header import decode_header
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type, Optional

class SecureEmailViewerInput(BaseModel):
    provider: str = Field(description="Email provider: 'gmail', 'outlook', 'yahoo', or 'custom'")
    folder: str = Field(default="inbox", description="Email folder to check (inbox, sent, drafts, etc.)")
    limit: int = Field(default=10, description="Maximum number of emails to fetch")
    mark_as_read: bool = Field(default=False, description="Whether to mark fetched emails as read")
    include_body: bool = Field(default=False, description="Whether to include email body in results")

class SecureEmailViewer(BaseTool):
    name: str = "secure_email_viewer"
    description: str = "Check emails from various providers with secure credential handling using environment variables"
    args_schema: Type[BaseModel] = SecureEmailViewerInput

    def _run(self, provider: str, folder: str = "inbox", limit: int = 10, mark_as_read: bool = False, include_body: bool = False) -> str:
        # Secure credential handling via environment variables
        email_address = os.getenv("EMAIL_ADDRESS")
        app_password = os.getenv("EMAIL_APP_PASSWORD")
        
        if not email_address or not app_password:
            return "Error: Email credentials not found in environment variables. Please set EMAIL_ADDRESS and EMAIL_APP_PASSWORD."
        
        # Determine IMAP server based on provider
        imap_server = ""
        if provider == "gmail":
            imap_server = "imap.gmail.com"
        elif provider == "outlook":
            imap_server = "outlook.office365.com"
        elif provider == "yahoo":
            imap_server = "imap.mail.yahoo.com"
        elif provider == "custom":
            imap_server = os.getenv("EMAIL_IMAP_SERVER")
            if not imap_server:
                return "Error: For custom provider, EMAIL_IMAP_SERVER environment variable must be set."
        else:
            return f"Error: Unsupported provider '{provider}'. Supported providers: gmail, outlook, yahoo, custom."
        
        try:
            # Connect to the server using SSL
            mail = imaplib.IMAP4_SSL(imap_server)
            mail.login(email_address, app_password)
            mail.select(folder)
            
            # Search for all emails in the folder
            status, messages = mail.search(None, "ALL")
            email_ids = messages[0].split()
            
            # Limit the number of emails to process
            email_ids = email_ids[-limit:] if len(email_ids) > limit else email_ids
            email_ids.reverse()  # Most recent first
            
            results = []
            for e_id in email_ids:
                status, msg_data = mail.fetch(e_id, "(RFC822)")
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        
                        # Decode subject
                        subject, encoding = decode_header(msg["Subject"])[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding if encoding else "utf-8")
                        
                        # Decode sender
                        sender, encoding = decode_header(msg.get("From"))[0]
                        if isinstance(sender, bytes):
                            sender = sender.decode(encoding if encoding else "utf-8")
                        
                        date = msg.get("Date")
                        
                        email_info = {
                            "subject": subject,
                            "sender": sender,
                            "date": date
                        }
                        
                        if include_body:
                            body = ""
                            if msg.is_multipart():
                                for part in msg.walk():
                                    content_type = part.get_content_type()
                                    content_disposition = str(part.get("Content-Disposition"))
                                    
                                    # Skip attachments
                                    if "attachment" not in content_disposition:
                                        if content_type == "text/plain":
                                            body = part.get_payload(decode=True).decode()
                                            break
                                        elif content_type == "text/html":
                                            body = part.get_payload(decode=True).decode()
                                            # Prefer plain text but keep HTML as fallback
                                            if not body:
                                                body = part.get_payload(decode=True).decode()
                            else:
                                body = msg.get_payload(decode=True).decode()
                            email_info["body"] = body
                        
                        results.append(email_info)
                        
                        # Mark as read if requested
                        if mark_as_read:
                            mail.store(e_id, '+FLAGS', '\\Seen')
            
            mail.close()
            mail.logout()
            
            # Format results for output
            output = []
            for i, email in enumerate(results, 1):
                output.append(f"Email {i}:")
                output.append(f"  Subject: {email['subject']}")
                output.append(f"  From: {email['sender']}")
                output.append(f"  Date: {email['date']}")
                if include_body and 'body' in email:
                    # Limit body length to prevent overwhelming output
                    body_preview = email['body'][:200] + "..." if len(email['body']) > 200 else email['body']
                    output.append(f"  Body: {body_preview}")
                output.append("")
            
            if not results:
                return f"No emails found in {folder} folder."
            
            return "\n".join(output)
            
        except imaplib.IMAP4.error as e:
            return f"IMAP error: {str(e)}. Please check your credentials and server settings."
        except Exception as e:
            # Avoid exposing sensitive information in error messages
            return "An error occurred while accessing email. Please check your configuration and try again."