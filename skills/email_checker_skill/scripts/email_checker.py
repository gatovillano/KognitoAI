import imaplib
import email
import os
import ssl
from email.header import decode_header
from typing import List, Dict, Any
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

class EmailCheckerInput(BaseModel):
    provider: str = Field(description="Email provider: 'gmail', 'outlook', 'yahoo', or 'custom'")
    folder: str = Field(default="inbox", description="Email folder to check (inbox, sent, drafts, etc.)")
    limit: int = Field(default=10, description="Maximum number of emails to fetch")
    mark_as_read: bool = Field(default=False, description="Whether to mark fetched emails as read")
    include_body: bool = Field(default=False, description="Whether to include email body in results")

class EmailChecker(BaseTool):
    name: str = "email_checker"
    description: str = "Check emails from various providers with secure credential handling"
    args_schema: type[BaseModel] = EmailCheckerInput

    def _get_imap_server(self, provider: str) -> str:
        """Get IMAP server for the given provider"""
        servers = {
            "gmail": "imap.gmail.com",
            "outlook": "outlook.office365.com",
            "yahoo": "imap.mail.yahoo.com"
        }
        if provider.lower() in servers:
            return servers[provider.lower()]
        elif provider.lower() == "custom":
            # For custom provider, server should be in EMAIL_IMAP_SERVER env var
            server = os.getenv("EMAIL_IMAP_SERVER")
            if not server:
                raise ValueError("For custom provider, EMAIL_IMAP_SERVER environment variable must be set")
            return server
        else:
            raise ValueError(f"Unsupported provider: {provider}. Supported: gmail, outlook, yahoo, custom")

    def _get_credentials(self) -> tuple[str, str]:
        """Get email credentials from environment variables"""
        email_addr = os.getenv("EMAIL_ADDRESS")
        if not email_addr:
            raise ValueError("EMAIL_ADDRESS environment variable not set")
        
        # Check for app-specific password or OAuth2 token
        app_password = os.getenv("EMAIL_APP_PASSWORD")
        if app_password:
            return email_addr, app_password
        
        # Check for regular password (less secure, not recommended)
        password = os.getenv("EMAIL_PASSWORD")
        if password:
            return email_addr, password
        
        # Check for OAuth2 (more complex implementation)
        # For simplicity, we'll note that OAuth2 would require additional libraries
        raise ValueError("No email credentials found. Set EMAIL_APP_PASSWORD or EMAIL_PASSWORD environment variable")

    def _decode_mime_words(self, s: str) -> str:
        """Decode MIME encoded words"""
        if s is None:
            return ""
        decoded_parts = decode_header(s)
        decoded_string = ""
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                if encoding:
                    decoded_string += part.decode(encoding)
                else:
                    decoded_string += part.decode('utf-8', errors='ignore')
            else:
                decoded_string += part
        return decoded_string

    def _run(self, provider: str, folder: str = "inbox", limit: int = 10, 
             mark_as_read: bool = False, include_body: bool = False) -> str:
        """Check emails from the specified provider"""
        try:
            # Get IMAP server
            imap_server = self._get_imap_server(provider)
            
            # Get credentials
            email_addr, password = self._get_credentials()
            
            # Create SSL context
            context = ssl.create_default_context()
            
            # Connect to IMAP server
            mail = imaplib.IMAP4_SSL(imap_server, ssl_context=context)
            
            # Login
            mail.login(email_addr, password)
            
            # Select folder
            status, messages = mail.select(folder)
            if status != 'OK':
                return f"Error: Could not select folder '{folder}'"
            
            # Search for all emails
            status, messages = mail.search(None, 'ALL')
            if status != 'OK':
                return "Error: Could not search emails"
            
            # Get email IDs
            email_ids = messages[0].split()
            
            # Limit the number of emails to fetch
            if limit > 0:
                email_ids = email_ids[-limit:]  # Get most recent emails
            
            emails_list = []
            
            for email_id in email_ids:
                # Fetch email
                status, msg_data = mail.fetch(email_id, '(RFC822)')
                if status != 'OK':
                    continue
                
                # Parse email
                raw_email = msg_data[0][1]
                email_message = email.message_from_bytes(raw_email)
                
                # Extract email details
                subject = self._decode_mime_words(email_message["Subject"])
                sender = self._decode_mime_words(email_message["From"])
                date = self._decode_mime_words(email_message["Date"])
                
                # Get email body if requested
                body = ""
                if include_body:
                    if email_message.is_multipart():
                        for part in email_message.walk():
                            content_type = part.get_content_type()
                            content_disposition = str(part.get("Content-Disposition"))
                            
                            # Skip attachments
                            if "attachment" in content_disposition:
                                continue
                            
                            if content_type == "text/plain" or content_type == "text/html":
                                try:
                                    body = part.get_payload(decode=True).decode()
                                    break
                                except:
                                    continue
                    else:
                        try:
                            body = email_message.get_payload(decode=True).decode()
                        except:
                            body = "Unable to decode body"
                
                # Mark as read if requested
                if mark_as_read:
                    mail.store(email_id, '+FLAGS', '\\Seen')
                
                # Add to results
                email_info = {
                    "id": email_id.decode(),
                    "subject": subject,
                    "from": sender,
                    "date": date,
                }
                if include_body:
                    email_info["body"] = body[:500] + "..." if len(body) > 500 else body  # Limit body length
                
                emails_list.append(email_info)
            
            # Close connection
            mail.close()
            mail.logout()
            
            # Format results
            if not emails_list:
                return f"No emails found in {folder} folder."
            
            result = f"Found {len(emails_list)} email(s) in {folder} folder:\n\n"
            for i, email_info in enumerate(emails_list, 1):
                result += f"{i}. Subject: {email_info['subject']}\n"
                result += f"   From: {email_info['from']}\n"
                result += f"   Date: {email_info['date']}\n"
                if include_body and 'body' in email_info:
                    result += f"   Body: {email_info['body']}\n"
                result += "\n"
            
            return result
            
        except imaplib.IMAP4.error as e:
            return f"IMAP Error: {str(e)}. Please check your credentials and server settings."
        except Exception as e:
            return f"Error: {str(e)}"