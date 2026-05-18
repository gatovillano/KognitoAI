"""
Cliente IMAP robusto y seguro para recuperación de correos.
 Maneja conexiones SSL, timeouts, reintentos y operaciones de correo.
"""

import asyncio
import ssl
import logging
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
from imap_tools import MailBox, MailBoxStartTls, MailBoxUnencrypted, AND
from imap_tools.errors import MailboxLoginError, MailboxLogoutError

logger = logging.getLogger(__name__)

@dataclass
class EmailMessage:
    """Representación de un mensaje de correo."""
    uid: str
    from_addr: str
    to_addr: List[str]
    cc_addr: List[str]
    subject: str
    date: datetime
    text_body: Optional[str] = None
    html_body: Optional[str] = None
    attachments: List[Dict[str, Any]] = None
    flags: List[str] = None
    size: int = 0
    
    def __post_init__(self):
        if self.attachments is None:
            self.attachments = []
        if self.flags is None:
            self.flags = []

class IMAPClient:
    """Cliente IMAP con manejo robusto de errores y reconexión."""
    
    def __init__(
        self,
        server: str,
        port: int,
        email: str,
        password: str,
        use_ssl: bool = True,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: int = 5
    ):
        self.server = server
        self.port = port
        self.email = email
        self.password = password
        self.use_ssl = use_ssl
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._mailbox: Optional[MailBox] = None
        self._connected = False
    
    def connect(self) -> None:
        """Establece conexión IMAP con reintentos."""
        last_error = None
        
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"Conectando a IMAP {self.server}:{self.port} (intento {attempt})")
                
                # Seleccionar clase de conexión según SSL
                if self.use_ssl and self.port != 993:
                    mailbox_class = MailBoxStartTls
                elif self.port == 993:
                    mailbox_class = MailBox
                else:
                    mailbox_class = MailBoxUnencrypted
                
                # Crear contexto SSL con verificación estricta
                ssl_context = None
                if self.use_ssl and self.port != 993:
                    ssl_context = ssl.create_default_context()
                    ssl_context.check_hostname = True
                    ssl_context.verify_mode = ssl.CERT_REQUIRED
                
                # Conectar
                self._mailbox = mailbox_class(
                    host=self.server,
                    port=self.port,
                    timeout=self.timeout,
                    ssl_context=ssl_context
                )
                
                # Login
                self._mailbox.login(self.email, self.password)
                self._connected = True
                
                logger.info(f"✅ Conectado exitosamente a {self.email}")
                return
                
            except MailboxLoginError as e:
                last_error = e
                logger.error(f"Error de autenticación: {e}")
                if attempt < self.max_retries:
                    logger.info(f"Reintentando en {self.retry_delay}s...")
                    asyncio.sleep(self.retry_delay)
                    
            except (ConnectionError, TimeoutError, OSError) as e:
                last_error = e
                logger.error(f"Error de conexión: {e}")
                if attempt < self.max_retries:
                    backoff = self.retry_delay * (2 ** (attempt - 1))
                    logger.info(f"Backoff exponencial: esperando {backoff}s...")
                    asyncio.sleep(backoff)
        
        # Si llegamos aquí, todos los reintentos fallaron
        raise ConnectionError(
            f"No se pudo conectar después de {self.max_retries} intentos. "
            f"Último error: {last_error}"
        )
    
    def disconnect(self) -> None:
        """Desconecta limpiamente."""
        if self._mailbox and self._connected:
            try:
                self._mailbox.logout()
                logger.info("Desconectado limpiamente")
            except Exception as e:
                logger.warning(f"Error al desconectar: {e}")
            finally:
                self._connected = False
                self._mailbox = None
    
    def _ensure_connected(self) -> None:
        """Asegura que hay conexión activa."""
        if not self._connected or not self._mailbox:
            raise ConnectionError("Cliente no conectado. Llama a connect() primero.")
    
    def get_folders(self) -> List[Dict[str, str]]:
        """Lista todas las carpetas/buzones disponibles."""
        self._ensure_connected()
        
        folders = []
        try:
            for folder in self._mailbox.folder.list():
                folders.append({
                    "name": folder.name,
                    "attributes": folder.flags,
                    "delimiter": folder.delim
                })
            logger.info(f"Encontradas {len(folders)} carpetas")
        except Exception as e:
            logger.error(f"Error listando carpetas: {e}")
            raise
        
        return folders
    
    def fetch_emails(
        self,
        folder: str = "INBOX",
        limit: int = 50,
        offset: int = 0,
        search_criteria: Optional[Dict[str, Any]] = None
    ) -> List[EmailMessage]:
        """Obtiene emails de una carpeta específica."""
        self._ensure_connected()
        
        emails = []
        
        try:
            # Seleccionar carpeta
            self._mailbox.folder.set(folder)
            logger.info(f"Buscando en carpeta: {folder}")
            
            # Construir criterios de búsqueda
            criteria = AND(all=True)  # Todos los emails
            if search_criteria:
                if search_criteria.get("from"):
                    criteria &= AND(from_=search_criteria["from"])
                if search_criteria.get("subject"):
                    criteria &= AND(subject=search_criteria["subject"])
                if search_criteria.get("date_after"):
                    criteria &= AND(date_gt=search_criteria["date_after"])
                if search_criteria.get("date_before"):
                    criteria &= AND(date_lt=search_criteria["date_before"])
                if search_criteria.get("seen") is not None:
                    criteria &= AND(seen=search_criteria["seen"])
            
            # Fetch de mensajes
            messages = self._mailbox.fetch(
                criteria=criteria,
                limit=limit,

                mark_seen=False,  # No marcar como leído
                bulk=False  # Paginación para evitar cuelgues con muchos emails
            )
            
            for msg in messages:
                email = EmailMessage(
                    uid=msg.uid,
                    from_addr=msg.from_,
                    to_addr=msg.to,
                    cc_addr=msg.cc or [],
                    subject=msg.subject or "(sin asunto)",
                    date=msg.date,
                    text_body=msg.text,
                    html_body=msg.html,
                    flags=msg.flags,
                    size=msg.size
                )
                emails.append(email)
            
            logger.info(f"✅ Obtenidos {len(emails)} emails de {folder}")
            
        except Exception as e:
            logger.error(f"Error obteniendo emails: {e}")
            raise
        
        return emails
    
    def fetch_email_by_uid(
        self,
        uid: str,
        folder: str = "INBOX",
        include_body: bool = True,
        include_attachments: bool = False
    ) -> Optional[EmailMessage]:
        """Obtiene un email específico por UID."""
        self._ensure_connected()
        
        try:
            self._mailbox.folder.set(folder)
            
            # Fetch del mensaje específico
            messages = self._mailbox.fetch(
                criteria=AND(uid=uid),
                mark_seen=False
            )
            
            if not messages:
                logger.warning(f"Email con UID {uid} no encontrado")
                return None
            
            msg = messages[0]
            
            email = EmailMessage(
                uid=msg.uid,
                from_addr=msg.from_,
                to_addr=msg.to,
                cc_addr=msg.cc or [],
                subject=msg.subject or "(sin asunto)",
                date=msg.date,
                text_body=msg.text if include_body else None,
                html_body=msg.html if include_body else None,
                flags=msg.flags,
                size=msg.size
            )
            
            # Procesar adjuntos si se solicita
            if include_attachments and msg.attachments:
                for att in msg.attachments:
                    email.attachments.append({
                        "filename": att.filename,
                        "content_type": att.content_type,
                        "size": att.size,
                        "payload": att.payload
                    })
            
            return email
            
        except Exception as e:
            logger.error(f"Error obteniendo email {uid}: {e}")
            raise
    
    def search_emails(
        self,
        query: str,
        folder: str = "INBOX",
        limit: int = 50
    ) -> List[EmailMessage]:
        """Búsqueda de emails por texto (remitente, asunto, cuerpo)."""
        self._ensure_connected()
        
        # Usar criterios AND para búsqueda
        criteria = AND()
        criteria &= AND(text=query)  # Busca en remitente, asunto y cuerpo
        
        try:
            self._mailbox.folder.set(folder)
            messages = self._mailbox.fetch(
                criteria=criteria,
                limit=limit,
                mark_seen=False
            )
            
            emails = []
            for msg in messages:
                email = EmailMessage(
                    uid=msg.uid,
                    from_addr=msg.from_,
                    to_addr=msg.to,
                    cc_addr=msg.cc or [],
                    subject=msg.subject or "(sin asunto)",
                    date=msg.date,
                    text_body=msg.text,
                    flags=msg.flags
                )
                emails.append(email)
            
            logger.info(f"Búsqueda '{query}' encontró {len(emails)} resultados")
            return emails
            
        except Exception as e:
            logger.error(f"Error en búsqueda: {e}")
            raise
    
    def get_unread_count(self, folder: str = "INBOX") -> int:
        """Obtiene cantidad de emails no leídos."""
        self._ensure_connected()
        
        try:
            self._mailbox.folder.set(folder)
            messages = self._mailbox.fetch(
                criteria=AND(seen=False),
                limit=1000,  # Límite alto para contar todos
                mark_seen=False
            )
            count = len(list(messages))
            logger.info(f"Emails no leídos en {folder}: {count}")
            return count
        except Exception as e:
            logger.error(f"Error contando no leídos: {e}")
            raise
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
        return False
