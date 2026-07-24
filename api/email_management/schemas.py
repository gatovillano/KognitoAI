from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List

class EmailConfigBase(BaseModel):
    provider: str = "custom"
    imap_server: Optional[str] = None
    imap_port: Optional[int] = 993
    imap_ssl: bool = True
    imap_user: Optional[str] = None
    smtp_server: Optional[str] = None
    smtp_port: Optional[int] = 465
    smtp_ssl: bool = True
    smtp_user: Optional[str] = None

class EmailConfigUpdate(EmailConfigBase):
    imap_password: Optional[str] = None
    smtp_password: Optional[str] = None
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None

class EmailConfigResponse(EmailConfigBase):
    has_imap_password: bool
    has_smtp_password: bool
    has_google_oauth: bool
    google_client_id: Optional[str] = None

    class Config:
        from_attributes = True

class EmailSendRequest(BaseModel):
    to_email: EmailStr
    cc_emails: Optional[List[EmailStr]] = []
    subject: str
    body: str

class AIDraftRequest(BaseModel):
    original_email_uid: Optional[str] = None
    instructions: str
    original_subject: Optional[str] = None
    original_body: Optional[str] = None
