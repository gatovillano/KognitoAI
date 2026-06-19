"""
Parser de correos electrónicos.
 Maneja HTML, texto plano, adjuntos y codificaciones de forma segura.
"""

import base64
import email
import logging
import re
from typing import Optional, Dict, List, Any, Tuple
from pathlib import Path
from email.header import decode_header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
import quopri
import hashlib

logger = logging.getLogger(__name__)

class EmailParser:
    """Parser seguro de mensajes MIME."""
    
    # Extensiones de archivo potencialmente peligrosas
    DANGEROUS_EXTENSIONS = {
        '.exe', '.bat', '.cmd', '.com', '.scr', '.vbs', '.js',
        '.jar', '.ps1', '.sh', '.msi', '.dll', '.pif', '.application'
    }
    
    # Límites de tamaño (bytes)
    MAX_ATTACHMENT_SIZE = 25 * 1024 * 1024  # 25 MB
    MAX_TEXT_BODY_SIZE = 10 * 1024 * 1024   # 10 MB
    
    def __init__(self, allowed_extensions: Optional[List[str]] = None):
        self.allowed_extensions = allowed_extensions or [
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.txt',
            '.jpg', '.jpeg', '.png', '.gif', '.zip', '.csv'
        ]
    
    def parse_raw_email(self, raw_bytes: bytes) -> Dict[str, Any]:
        """Parsea un email en formato MIME desde bytes crudos."""
        try:
            msg = email.message_from_bytes(raw_bytes)
            return self._parse_message(msg)
        except Exception as e:
            logger.error(f"Error parseando email: {e}")
            raise ValueError(f"Email malformado: {e}")
    
    def _parse_message(self, msg: email.message.Message) -> Dict[str, Any]:
        """Parseo recursivo de mensaje MIME."""
        result = {
            "headers": {},
            "subject": "",
            "from": "",
            "to": [],
            "cc": [],
            "date": "",
            "text_body": "",
            "html_body": "",
            "attachments": [],
            "size": 0
        }
        
        # Parsear headers
        for key in msg.keys():
            value, encoding = decode_header(msg[key])[0]
            if isinstance(value, bytes):
                try:
                    value = value.decode(encoding or 'utf-8', errors='replace')
                except:
                    value = value.decode('latin-1', errors='replace')
            result["headers"][key.lower()] = value
        
        # Extraer campos principales
        result["subject"] = result["headers"].get("subject", "")
        result["from"] = result["headers"].get("from", "")
        result["date"] = result["headers"].get("date", "")
        
        # Parsear destinatarios
        to_header = result["headers"].get("to", "")
        cc_header = result["headers"].get("cc", "")
        result["to"] = self._parse_addresses(to_header)
        result["cc"] = self._parse_addresses(cc_header)
        
        # Parsear cuerpo y adjuntos
        if msg.is_multipart():
            result = self._parse_multipart(msg, result)
        else:
            result = self._parse_single_part(msg, result)
        
        # Calcular tamaño
        result["size"] = len(msg.as_bytes())
        
        return result
    
    def _parse_addresses(self, header: str) -> List[str]:
        """Parsea direcciones de correo From/To/Cc."""
        if not header:
            return []
        
        addresses = []
        # Patrón simple para extraer emails
        pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
        matches = re.findall(pattern, header)
        
        for match in matches:
            addresses.append(match.lower())
        
        return list(set(addresses))  # Eliminar duplicados
    
    def _parse_multipart(
        self, 
        msg: MIMEMultipart, 
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parseo de mensajes multipart (HTML + texto + adjuntos)."""
        
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get_content_disposition() or "")
            
            # Es un adjunto
            if "attachment" in content_disposition:
                result["attachments"].append(
                    self._parse_attachment(part)
                )
            
            # Es parte del cuerpo
            elif content_type == "text/plain":
                body = self._decode_part(part)
                if body:
                    result["text_body"] += body + "\n"
            
            elif content_type == "text/html":
                body = self._decode_part(part)
                if body:
                    result["html_body"] += body + "\n"
            
            # Texto en formato alternativo
            elif content_type.startswith("text/"):
                body = self._decode_part(part)
                if body and not result["text_body"]:
                    result["text_body"] = body
        
        # Limitar tamaños
        if len(result["text_body"]) > self.MAX_TEXT_BODY_SIZE:
            result["text_body"] = (result["text_body"][:self.MAX_TEXT_BODY_SIZE] + 
                                   "\n... [TRUNCADO]")
        
        if len(result["html_body"]) > self.MAX_TEXT_BODY_SIZE:
            result["html_body"] = (result["html_body"][:self.MAX_TEXT_BODY_SIZE] + 
                                   "\n... [TRUNCADO]")
        
        return result
    
    def _parse_single_part(
        self, 
        msg: email.message.Message, 
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parseo de mensajes de una sola parte."""
        content_type = msg.get_content_type()
        
        if content_type == "text/plain":
            result["text_body"] = self._decode_part(msg)
        elif content_type == "text/html":
            result["html_body"] = self._decode_part(msg)
        
        return result
    
    def _decode_part(self, part: email.message.Message) -> str:
        """Decodifica el contenido de una parte del mensaje."""
        try:
            payload = part.get_payload(decode=True)
            if not payload:
                return ""
            
            # Detectar codificación
            charset = part.get_content_charset() or 'utf-8'
            
            try:
                return payload.decode(charset, errors='replace')
            except (UnicodeDecodeError, LookupError):
                # Fallback a latin-1
                return payload.decode('latin-1', errors='replace')
                
        except Exception as e:
            logger.warning(f"Error decodificando parte: {e}")
            return ""
    
    def _parse_attachment(self, part: email.message.Message) -> Dict[str, Any]:
        """Parsea un adjunto de forma segura."""
        try:
            filename = part.get_filename()
            if not filename:
                # Generar nombre genérico
                filename = f"adjunto_{part.get_content_type().replace('/', '_')}"
            
            # Decodificar nombre del archivo
            decoded_filename = self._decode_filename(filename)
            
            # Validar extensión
            file_ext = Path(decoded_filename).suffix.lower()
            
            # Verificar si es peligroso
            is_dangerous = file_ext in self.DANGEROUS_EXTENSIONS
            
            # Obtener contenido
            payload = part.get_payload(decode=True)
            size = len(payload) if payload else 0
            
            # Verificar tamaño
            is_too_large = size > self.MAX_ATTACHMENT_SIZE
            
            # Calcular hash para verificación de integridad
            content_hash = hashlib.sha256(payload).hexdigest() if payload else None
            
            attachment = {
                "filename": decoded_filename,
                "original_filename": filename,
                "content_type": part.get_content_type(),
                "size": size,
                "is_dangerous": is_dangerous,
                "is_too_large": is_too_large,
                "content_hash": content_hash,
                "safe_to_save": (not is_dangerous and not is_too_large)
            }
            
            if is_dangerous:
                logger.warning(f"Adjunto potencialmente peligroso: {decoded_filename}")
            
            if is_too_large:
                logger.warning(f"Adjunto muy grande: {decoded_filename} ({size} bytes)")
            
            return attachment
            
        except Exception as e:
            logger.error(f"Error parseando adjunto: {e}")
            return {
                "filename": "error.bin",
                "error": str(e),
                "safe_to_save": False
            }
    
    def _decode_filename(self, filename: str) -> str:
        """Decodifica nombre de archivo con codificación MIME."""
        try:
            decoded_parts = decode_header(filename)
            result = ""
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    result += part.decode(encoding or 'utf-8', errors='replace')
                else:
                    result += str(part)
            return result
        except:
            return filename
    
    def strip_html(self, html: str) -> str:
        """Convierte HTML a texto plano de forma segura."""
        # Implementación simple sin dependencias externas
        # Remover tags
        text = re.sub(r'<[^>]+>', ' ', html)
        # Decodificar entidades HTML básicas
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&amp;', '&')
        text = text.replace('&quot;', '"')
        text = text.replace('&#39;', "'")
        # Normalizar espacios
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def save_attachment(
        self, 
        attachment: Dict[str, Any], 
        directory: str,
        overwrite: bool = False
    ) -> Optional[str]:
        """Guarda un adjunto en disco de forma segura."""
        if not attachment.get("safe_to_save", False):
            raise ValueError(
                f"Adjunto no seguro para guardar: {attachment.get('filename')}. "
                f"Peligroso: {attachment.get('is_dangerous')}, "
                f"Muy grande: {attachment.get('is_too_large')}"
            )
        
        try:
            save_dir = Path(directory)
            save_dir.mkdir(parents=True, exist_ok=True)
            
            filepath = save_dir / attachment["filename"]
            
            # Manejar nombres duplicados
            if filepath.exists() and not overwrite:
                stem = filepath.stem
                suffix = filepath.suffix
                counter = 1
                while filepath.exists():
                    filepath = save_dir / f"{stem}_{counter}{suffix}"
                    counter += 1
            
            # Guardar archivo
            with open(filepath, 'wb') as f:
                f.write(attachment.get('payload', b''))
            
            logger.info(f"Adjunto guardado: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Error guardando adjunto: {e}")
            raise
