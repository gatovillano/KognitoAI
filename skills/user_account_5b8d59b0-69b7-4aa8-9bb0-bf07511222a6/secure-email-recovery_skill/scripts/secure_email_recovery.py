"""
Skill: Recuperación Segura de Correos Electrónicos
=============================================================
Soporta: Gmail, Outlook, Yahoo, Disroot y cualquier proveedor IMAP.
Características: OAuth2, contraseña, caché, reintentos automáticos, logging.
"""

import os
import sys
import json
import asyncio
import logging
import argparse
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Importar componentes locales
from auth_manager import AuthManager, AuthCredentials
from imap_client import IMAPClient, EmailMessage
from email_parser import EmailParser
from cache_manager import EmailCache, get_default_cache
from error_handler import ErrorHandler, EmailRecoveryError, ErrorCategory

# =============================================================================
# CONFIGURACIÓN DE PROVEEDORES
# =============================================================================

PROVIDERS = {
    "disroot": {
        "display_name": "Disroot",
        "imap_server": "disroot.org",
        "imap_port": 993,
        "smtp_server": "disroot.org",
        "smtp_port": 465,
        "use_ssl": True,
        "auth_methods": ["password"],
        "notes": "Requiere contraseña de aplicación generada en el panel de Disroot"
    },
    "gmail": {
        "display_name": "Gmail/Google Workspace",
        "imap_server": "imap.gmail.com",
        "imap_port": 993,
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 465,
        "use_ssl": True,
        "auth_methods": ["oauth2", "app_password"],
        "oauth2_scopes": ["https://mail.google.com/"],
        "notes": "Requiere OAuth2 configurado o contraseña de aplicación"
    },
    "outlook": {
        "display_name": "Outlook/Office 365",
        "imap_server": "outlook.office365.com",
        "imap_port": 993,
        "smtp_server": "smtp.office365.com",
        "smtp_port": 587,
        "use_ssl": True,
        "auth_methods": ["oauth2", "app_password"],
        "oauth2_scopes": ["https://outlook.office.com/IMAP.AccessAsUser.All"],
        "notes": "Requiere OAuth2 configurado o contraseña de aplicación"
    },
    "yahoo": {
        "display_name": "Yahoo Mail",
        "imap_server": "imap.mail.yahoo.com",
        "imap_port": 993,
        "smtp_server": "smtp.mail.yahoo.com",
        "smtp_port": 465,
        "use_ssl": True,
        "auth_methods": ["oauth2", "app_password"],
        "oauth2_scopes": ["mail-r", "mail-w"],
        "notes": "Requiere OAuth2 configurado o contraseña de aplicación"
    },
    "generic": {
        "display_name": "Proveedor IMAP Genérico",
        "imap_server": None,  # Debe especificarse
        "imap_port": 993,
        "smtp_server": None,
        "smtp_port": 465,
        "use_ssl": True,
        "auth_methods": ["password"],
        "notes": "Para servidores IMAP personalizados"
    }
}

# =============================================================================
# CLASE PRINCIPAL: EmailRecovery
# =============================================================================

class EmailRecovery:
    """Cliente principal para recuperación segura de correos."""
    
    def __init__(
        self,
        provider: str,
        email: str,
        password: Optional[str] = None,
        imap_server: Optional[str] = None,
        imap_port: Optional[int] = None,
        use_cache: bool = True,
        cache_ttl: int = 300,
        max_retries: int = 3,
        timeout: int = 30
    ):
        """
        Inicializa el cliente de recuperación de correo.
        
        Args:
            provider: Nombre del proveedor (disroot, gmail, outlook, yahoo, generic)
            email: Dirección de correo electrónico
            password: Contraseña o contraseña de aplicación (si es necesario)
            imap_server: Servidor IMAP personalizado (para proveedor 'generic')
            imap_port: Puerto IMAP personalizado
            use_cache: Si usar caché para acelerar consultas repetidas
            cache_ttl: Tiempo de vida de caché en segundos
            max_retries: Número máximo de reintentos en errores recuperables
            timeout: Timeout de conexión en segundos
        """
        self.provider = provider.lower()
        self.email = email
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Validar proveedor
        if self.provider not in PROVIDERS:
            raise ValueError(
                f"Proveedor '{self.provider}' no soportado. "
                f"Opciones: {list(PROVIDERS.keys())}"
            )
        
        # Obtener configuración del proveedor
        provider_config = PROVIDERS[self.provider]
        self.imap_server = imap_server or provider_config["imap_server"]
        self.imap_port = imap_port or provider_config["imap_port"]
        self.use_ssl = provider_config["use_ssl"]
        
        if not self.imap_server:
            raise ValueError(
                f"Debes especificar imap_server para el proveedor '{self.provider}'"
            )
        
        # Inicializar componentes
        self.auth = AuthManager(self.provider, self.email)
        self.parser = EmailParser()
        self.cache = get_default_cache() if use_cache else None
        
        # Obtener contraseña (desde parámetro o variables de entorno)
        self.password = password or self.auth.get_password()
        
        # Cliente IMAP (se inicializa al conectar)
        self._client: Optional[IMAPClient] = None
        
        logger.info(f"Cliente inicializado: {self.provider} / {self.email}")
    
    def connect(self) -> None:
        """Establece conexión IMAP."""
        try:
            self._client = IMAPClient(
                server=self.imap_server,
                port=self.imap_port,
                email=self.email,
                password=self.password,
                use_ssl=self.use_ssl,
                timeout=self.timeout,
                max_retries=self.max_retries
            )
            self._client.connect()
        except EmailRecoveryError:
            raise
        except Exception as e:
            error = ErrorHandler.handle_exception(e, {
                "operation": "connect",
                "email": self.email,
                "provider": self.provider
            })
            raise error
    
    def disconnect(self) -> None:
        """Desconecta del servidor IMAP."""
        if self._client:
            self._client.disconnect()
            self._client = None
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        return False
    
    # =========================================================================
    # MÉTODOS PÚBLICOS DE RECUPERACIÓN
    # =========================================================================
    
    def get_recent_emails(
        self,
        folder: str = "INBOX",
        limit: int = 50,
        use_cache: bool = True
    ) -> List[EmailMessage]:
        """
        Obtiene los emails más recientes de una carpeta.
        
        Args:
            folder: Nombre de la carpeta (INBOX, Sent, Drafts, etc.)
            limit: Número máximo de emails a obtener
            use_cache: Si usar caché para esta consulta
        
        Returns:
            Lista de EmailMessage
        """
        # Verificar caché
        if use_cache and self.cache:
            cached = self.cache.get(
                operation="get_recent_emails",
                email=self.email,
                folder=folder,
                limit=limit
            )
            if cached is not None:
                return cached
        
        try:
            emails = self._client.fetch_emails(folder=folder, limit=limit)
            
            # Guardar en caché
            if use_cache and self.cache:
                self.cache.set(
                    operation="get_recent_emails",
                    email=self.email,
                    folder=folder,
                    limit=limit,
                    value=emails
                )
            
            return emails
            
        except Exception as e:
            error = ErrorHandler.handle_exception(e, {
                "operation": "get_recent_emails",
                "email": self.email,
                "folder": folder
            })
            raise error
    
    def get_email_by_uid(
        self,
        uid: str,
        folder: str = "INBOX",
        include_body: bool = True,
        attachment_dir: Optional[str] = None
    ) -> Optional[EmailMessage]:
        """
        Obtiene un email específico por su UID.
        
        Args:
            uid: Identificador único del email
            folder: Carpeta donde buscar
            include_body: Si incluir cuerpo del mensaje
            attachment_dir: Directorio para guardar adjuntos (opcional)
        
        Returns:
            EmailMessage o None si no existe
        """
        try:
            email = self._client.fetch_email_by_uid(
                uid=uid,
                folder=folder,
                include_body=include_body,
                include_attachments=bool(attachment_dir)
            )
            
            # Guardar adjuntos si se solicita
            if email and attachment_dir and email.attachments:
                for att in email.attachments:
                    try:
                        self.parser.save_attachment(att, attachment_dir)
                    except Exception as e:
                        logger.warning(f"No se pudo guardar adjunto {att.get('filename')}: {e}")
            
            return email
            
        except Exception as e:
            error = ErrorHandler.handle_exception(e, {
                "operation": "get_email_by_uid",
                "email": self.email,
                "uid": uid,
                "folder": folder
            })
            raise error
    
    def search_emails(
        self,
        query: str,
        folder: str = "INBOX",
        limit: int = 50,
        use_cache: bool = True
    ) -> List[EmailMessage]:
        """
        Busca emails por texto (remitente, asunto, cuerpo).
        
        Args:
            query: Término de búsqueda
            folder: Carpeta donde buscar
            limit: Máximo de resultados
            use_cache: Si usar caché
        
        Returns:
            Lista de EmailMessage que coinciden
        """
        if use_cache and self.cache:
            cached = self.cache.get(
                operation="search_emails",
                email=self.email,
                folder=folder,
                query=query,
                limit=limit
            )
            if cached is not None:
                return cached
        
        try:
            emails = self._client.search_emails(
                query=query,
                folder=folder,
                limit=limit
            )
            
            if use_cache and self.cache:
                self.cache.set(
                    operation="search_emails",
                    email=self.email,
                    folder=folder,
                    query=query,
                    limit=limit,
                    value=emails
                )
            
            return emails
            
        except Exception as e:
            error = ErrorHandler.handle_exception(e, {
                "operation": "search_emails",
                "email": self.email,
                "query": query,
                "folder": folder
            })
            raise error
    
    def get_unread_count(self, folder: str = "INBOX") -> int:
        """Obtiene cantidad de emails no leídos en una carpeta."""
        try:
            return self._client.get_unread_count(folder)
        except Exception as e:
            error = ErrorHandler.handle_exception(e, {
                "operation": "get_unread_count",
                "email": self.email,
                "folder": folder
            })
            raise error
    
    def get_folders(self) -> List[Dict[str, str]]:
        """Lista todas las carpetas/buzones disponibles."""
        try:
            return self._client.get_folders()
        except Exception as e:
            error = ErrorHandler.handle_exception(e, {
                "operation": "get_folders",
                "email": self.email
            })
            raise error
    
    # =========================================================================
    # MÉTODOS DE UTILIDAD
    # =========================================================================
    
    def validate_configuration(self) -> Dict[str, Any]:
        """Valida que la configuración sea correcta."""
        auth_result = self.auth.validate_configuration()
        
        result = {
            "provider": self.provider,
            "email": self.email,
            "auth": auth_result,
            "imap_server": self.imap_server,
            "imap_port": self.imap_port,
            "use_ssl": self.use_ssl,
            "valid": False,
            "issues": []
        }
        
        if not auth_result["valid"]:
            result["issues"].extend(auth_result["issues"])
        
        # Verificar que el proveedor tenga configuración
        if self.provider in PROVIDERS:
            config = PROVIDERS[self.provider]
            if not config.get("imap_server") and self.provider == "generic":
                result["issues"].append("Proveedor 'generic' requiere imap_server")
        
        result["valid"] = len(result["issues"]) == 0
        
        return result
    
    def clear_cache(self) -> None:
        """Limpia la caché de este email."""
        if self.cache:
            count = self.cache.invalidate_all(self.email)
            logger.info(f"Caché limpiada: {count} entradas eliminadas")
    
    def get_cache_stats(self) -> Optional[Dict[str, Any]]:
        """Obtiene estadísticas de caché."""
        if self.cache:
            return self.cache.get_stats()
        return None

# =============================================================================
# INTERFAZ CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Recuperación segura de correos electrónicos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:

  # Obtener últimos 10 emails de INBOX
  python secure-email-recovery.py --provider disroot --email tu@disroot.org --recent --limit 10
  
  # Buscar emails por asunto
  python secure-email-recovery.py --provider disroot --email tu@disroot.org --search "factura" --limit 20
  
  # Obtener email específico por UID
  python secure-email-recovery.py --provider disroot --email tu@disroot.org --uid 123 --json
  
  # Listar carpetas
  python secure-email-recovery.py --provider disroot --email tu@disroot.org --folders
  
  # Validar configuración
  python secure-email-recovery.py --provider disroot --email tu@disroot.org --validate
        """
    )
    
    parser.add_argument("--provider", required=True, 
                        help="Proveedor: disroot, gmail, outlook, yahoo, generic")
    parser.add_argument("--email", required=True,
                        help="Dirección de correo electrónico")
    parser.add_argument("--password", 
                        help="Contraseña (si no se usa variable de entorno)")
    parser.add_argument("--imap-server",
                        help="Servidor IMAP personalizado (para proveedor 'generic')")
    parser.add_argument("--imap-port", type=int,
                        help="Puerto IMAP personalizado")
    
    # Acciones
    parser.add_argument("--recent", action="store_true",
                        help="Obtener emails recientes")
    parser.add_argument("--search", type=str,
                        help="Buscar emails por texto")
    parser.add_argument("--uid", type=str,
                        help="Obtener email por UID específico")
    parser.add_argument("--folders", action="store_true",
                        help="Listar carpetas disponibles")
    parser.add_argument("--unread", action="store_true",
                        help="Contar emails no leídos")
    parser.add_argument("--validate", action="store_true",
                        help="Validar configuración")
    
    # Opciones
    parser.add_argument("--limit", type=int, default=50,
                        help="Límite de resultados (por defecto: 50)")
    parser.add_argument("--folder", default="INBOX",
                        help="Carpeta IMAP (por defecto: INBOX)")
    parser.add_argument("--json", action="store_true",
                        help="Salida en formato JSON")
    parser.add_argument("--no-cache", action="store_true",
                        help="Desactivar caché")
    parser.add_argument("--attachment-dir",
                        help="Directorio para guardar adjuntos")
    
    args = parser.parse_args()
    
    # Crear cliente
    try:
        client = EmailRecovery(
            provider=args.provider,
            email=args.email,
            password=args.password,
            imap_server=args.imap_server,
            imap_port=args.imap_port,
            use_cache=not args.no_cache
        )
    except Exception as e:
        logger.error(f"Error inicializando cliente: {e}")
        sys.exit(1)
    
    # Ejecutar acción
    try:
        with client:
            # Validar configuración
            if args.validate:
                result = client.validate_configuration()
                print(json.dumps(result, indent=2, ensure_ascii=False))
                sys.exit(0 if result["valid"] else 1)
            
            # Listar carpetas
            if args.folders:
                folders = client.get_folders()
                if args.json:
                    print(json.dumps(folders, indent=2, ensure_ascii=False))
                else:
                    print(f"\n📁 Carpetas en {args.email}:")
                    print("=" * 50)
                    for f in folders:
                        attrs = ", ".join(f.get("attributes", []))
                        print(f"  📂 {f['name']}")
                        if attrs:
                            print(f"     Atributos: {attrs}")
                sys.exit(0)
            
            # Contar no leídos
            if args.unread:
                count = client.get_unread_count(args.folder)
                if args.json:
                    print(json.dumps({"unread_count": count}, indent=2))
                else:
                    print(f"📬 Emails no leídos en {args.folder}: {count}")
                sys.exit(0)
            
            # Buscar emails
            if args.search:
                emails = client.search_emails(
                    query=args.search,
                    folder=args.folder,
                    limit=args.limit
                )
                _output_emails(emails, args.json, args.attachment_dir)
                sys.exit(0)
            
            # Obtener email por UID
            if args.uid:
                email = client.get_email_by_uid(
                    uid=args.uid,
                    folder=args.folder,
                    include_body=True,
                    attachment_dir=args.attachment_dir
                )
                if email:
                    _output_email(email, args.json)
                else:
                    print(f"❌ Email con UID {args.uid} no encontrado")
                    sys.exit(1)
                sys.exit(0)
            
            # Obtener emails recientes (por defecto)
            if args.recent or not any([args.validate, args.folders, args.unread, args.search, args.uid]):
                emails = client.get_recent_emails(
                    folder=args.folder,
                    limit=args.limit
                )
                _output_emails(emails, args.json, args.attachment_dir)
                sys.exit(0)
    
    except EmailRecoveryError as e:
        logger.error(f"Error: {e}")
        if e.retry_after:
            logger.info(f"Reintenta en {e.retry_after} segundos")
        sys.exit(1)
    
    except KeyboardInterrupt:
        logger.info("Interrumpido por usuario")
        sys.exit(130)
    
    except Exception as e:
        logger.error(f"Error inesperado: {e}", exc_info=True)
        sys.exit(1)


def _output_emails(
    emails: List[EmailMessage],
    json_output: bool = False,
    attachment_dir: Optional[str] = None
) -> None:
    """Formatea y muestra lista de emails."""
    if json_output:
        data = []
        for email in emails:
            data.append(_email_to_dict(email))
        print(json.dumps(data, indent=2, ensure_ascii=False, default=str))
    else:
        if not emails:
            print("📭 No se encontraron emails")
            return
        
        print(f"\n📬 {len(emails)} emails encontrados:")
        print("=" * 80)
        
        for i, email in enumerate(emails, 1):
            print(f"\n[{i}] {email.subject}")
            print(f"    📧 De: {email.from_addr}")
            print(f"    📅 Fecha: {email.date.strftime('%Y-%m-%d %H:%M') if email.date else 'N/A'}")
            print(f"    🆔 UID: {email.uid}")
            if email.attachments:
                print(f"    📎 Adjuntos: {len(email.attachments)}")
                for att in email.attachments[:3]:
                    print(f"       - {att.get('filename', 'desconocido')} ({att.get('size', 0)//1024} KB)")
            print(f"    🔖 Flags: {', '.join(email.flags) if email.flags else 'ninguno'}")


def _output_email(email: EmailMessage, json_output: bool = False) -> None:
    """Formatea y muestra un email individual."""
    if json_output:
        print(json.dumps(_email_to_dict(email), indent=2, ensure_ascii=False, default=str))
    else:
        print(f"\n📧 Email: {email.subject}")
        print("=" * 80)
        print(f"De: {email.from_addr}")
        print(f"Para: {', '.join(email.to_addr)}")
        if email.cc_addr:
            print(f"CC: {', '.join(email.cc_addr)}")
        print(f"Fecha: {email.date.strftime('%Y-%m-%d %H:%M:%S') if email.date else 'N/A'}")
        print(f"UID: {email.uid}")
        print(f"Tamaño: {email.size:,} bytes")
        print(f"Flags: {', '.join(email.flags) if email.flags else 'ninguno'}")
        
        if email.text_body:
            print(f"\n📝 Cuerpo (texto):")
            print("-" * 80)
            print(email.text_body[:2000] + ("..." if len(email.text_body) > 2000 else ""))
        
        if email.html_body and not email.text_body:
            print(f"\n🌐 Cuerpo (HTML - primeros 1000 caracteres):")
            print("-" * 80)
            print(email.html_body[:1000] + "...")
        
        if email.attachments:
            print(f"\n📎 Adjuntos ({len(email.attachments)}):")
            for att in email.attachments:
                print(f"  • {att.get('filename', 'desconocido')}")
                print(f"    Tipo: {att.get('content_type', 'desconocido')}")
                print(f"    Tamaño: {att.get('size', 0):,} bytes")
                print(f"    Hash SHA256: {att.get('content_hash', 'N/A')[:16]}...")


def _email_to_dict(email: EmailMessage) -> Dict[str, Any]:
    """Convierte EmailMessage a diccionario serializable."""
    return {
        "uid": email.uid,
        "subject": email.subject,
        "from": email.from_addr,
        "to": email.to_addr,
        "cc": email.cc_addr,
        "date": email.date.isoformat() if email.date else None,
        "text_body": email.text_body,
        "html_body": email.html_body,
        "attachments": email.attachments,
        "flags": email.flags,
        "size": email.size
    }


if __name__ == "__main__":
    main()
