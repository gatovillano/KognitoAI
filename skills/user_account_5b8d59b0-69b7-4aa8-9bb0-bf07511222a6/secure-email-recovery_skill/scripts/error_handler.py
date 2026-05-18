"""
Manejador de errores estructurado para recuperación de correos.
 Clasifica errores, decide si son recuperables y genera mensajes útiles.
"""

import logging
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime
import traceback

logger = logging.getLogger(__name__)

class ErrorSeverity(Enum):
    """Niveles de severidad de errores."""
    LOW = "low"           # Error menor, no afecta funcionalidad
    MEDIUM = "medium"     # Error recuperable, afecta operación actual
    HIGH = "high"         # Error grave, requiere intervención
    CRITICAL = "critical" # Error sistema, no se puede continuar

class ErrorCategory(Enum):
    """Categorías de errores."""
    AUTHENTICATION = "authentication"  # Credenciales/permisos
    NETWORK = "network"                # Conexión/timeout
    IMAP = "imap"                      # Errores específicos IMAP
    PARSING = "parsing"                # Errores parseando correos
    FILESYSTEM = "filesystem"          # Errores guardando archivos
    RATE_LIMIT = "rate_limit"          # Límite de tasa excedido
    CONFIGURATION = "configuration"    # Configuración inválida
    UNKNOWN = "unknown"                # Error no clasificado

class EmailRecoveryError(Exception):
    """Excepción personalizada para errores de recuperación de correo."""
    
    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        recoverable: bool = True,
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.recoverable = recoverable
        self.retry_after = retry_after  # Segundos a esperar antes de reintentar
        self.details = details or {}
        self.original_exception = original_exception
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte el error a diccionario para logging/serialización."""
        result = {
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "recoverable": self.recoverable,
            "timestamp": self.timestamp.isoformat()
        }
        
        if self.retry_after:
            result["retry_after"] = self.retry_after
        
        if self.details:
            result["details"] = self.details
        
        if self.original_exception:
            result["original_exception"] = {
                "type": type(self.original_exception).__name__,
                "message": str(self.original_exception)
            }
        
        return result
    
    def __str__(self) -> str:
        return f"[{self.category.value.upper()}] {self.message}"

class ErrorHandler:
    """Manejador centralizado de errores."""
    
    # Mapeo de excepciones conocidas a categorías
    EXCEPTION_MAPPING = {
        # Errores de autenticación
        "MailboxLoginError": (ErrorCategory.AUTHENTICATION, ErrorSeverity.HIGH, False),
        "imaplib.IMAP4.error": (ErrorCategory.AUTHENTICATION, ErrorSeverity.HIGH, False),
        "imaplib.IMAP4.autherror": (ErrorCategory.AUTHENTICATION, ErrorSeverity.HIGH, False),
        
        # Errores de red
        "ConnectionError": (ErrorCategory.NETWORK, ErrorSeverity.MEDIUM, True),
        "TimeoutError": (ErrorCategory.NETWORK, ErrorSeverity.MEDIUM, True),
        "socket.timeout": (ErrorCategory.NETWORK, ErrorSeverity.MEDIUM, True),
        "socket.error": (ErrorCategory.NETWORK, ErrorSeverity.MEDIUM, True),
        "requests.exceptions.ConnectionError": (ErrorCategory.NETWORK, ErrorSeverity.MEDIUM, True),
        "requests.exceptions.Timeout": (ErrorCategory.NETWORK, ErrorSeverity.MEDIUM, True),
        
        # Errores IMAP
        "imaplib.IMAP4.abort": (ErrorCategory.IMAP, ErrorSeverity.HIGH, True),
        "imaplib.IMAP4.readonly": (ErrorCategory.IMAP, ErrorSeverity.MEDIUM, False),
        
        # Errores de parsing
        "email.errors.HeaderParseError": (ErrorCategory.PARSING, ErrorSeverity.LOW, True),
        "binascii.Error": (ErrorCategory.PARSING, ErrorSeverity.LOW, True),
        
        # Errores de sistema de archivos
        "FileNotFoundError": (ErrorCategory.FILESYSTEM, ErrorSeverity.MEDIUM, False),
        "PermissionError": (ErrorCategory.FILESYSTEM, ErrorSeverity.HIGH, False),
        "IsADirectoryError": (ErrorCategory.FILESYSTEM, ErrorSeverity.MEDIUM, False),
        
        # Errores de configuración
        "ValueError": (ErrorCategory.CONFIGURATION, ErrorSeverity.HIGH, False),
        "KeyError": (ErrorCategory.CONFIGURATION, ErrorSeverity.HIGH, False),
        "TypeError": (ErrorCategory.CONFIGURATION, ErrorSeverity.HIGH, False),
    }
    
    @classmethod
    def handle_exception(
        cls,
        exception: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> EmailRecoveryError:
        """
        Convierte una excepción genérica en EmailRecoveryError estructurada.
        
        Args:
            exception: La excepción original
            context: Contexto adicional (email, operación, etc.)
        
        Returns:
            EmailRecoveryError con toda la información clasificada
        """
        context = context or {}
        exc_type = type(exception).__name__
        exc_module = type(exception).__module__
        exc_full_name = f"{exc_module}.{exc_type}" if exc_module != "builtins" else exc_type
        
        # Buscar en el mapeo
        mapped = cls.EXCEPTION_MAPPING.get(exc_full_name) or cls.EXCEPTION_MAPPING.get(exc_type)
        
        if mapped:
            category, severity, recoverable = mapped
        else:
            # Clasificar por mensaje si es posible
            msg = str(exception).lower()
            
            if "login" in msg or "authentication" in msg or "credentials" in msg:
                category, severity, recoverable = (
                    ErrorCategory.AUTHENTICATION, ErrorSeverity.HIGH, False
                )
            elif "timeout" in msg or "timed out" in msg:
                category, severity, recoverable = (
                    ErrorCategory.NETWORK, ErrorSeverity.MEDIUM, True
                )
            elif "connection" in msg or "network" in msg:
                category, severity, recoverable = (
                    ErrorCategory.NETWORK, ErrorSeverity.MEDIUM, True
                )
            elif "rate" in msg or "too many" in msg or "limit" in msg:
                category, severity, recoverable = (
                    ErrorCategory.RATE_LIMIT, ErrorSeverity.MEDIUM, True
                )
            else:
                category, severity, recoverable = (
                    ErrorCategory.UNKNOWN, ErrorSeverity.MEDIUM, True
                )
        
        # Determinar tiempo de espera para reintentos
        retry_after = None
        if category == ErrorCategory.RATE_LIMIT:
            retry_after = 60  # Esperar 1 minuto por defecto
        elif category == ErrorCategory.NETWORK:
            retry_after = 5   # Esperar 5 segundos
        elif category == ErrorCategory.IMAP:
            retry_after = 10  # Esperar 10 segundos
        
        # Construir mensaje descriptivo
        message = cls._build_message(exception, category, context)
        
        # Crear error estructurado
        error = EmailRecoveryError(
            message=message,
            category=category,
            severity=severity,
            recoverable=recoverable,
            retry_after=retry_after,
            details={
                "exception_type": exc_type,
                "context": context,
                "traceback": traceback.format_exc() if severity != ErrorSeverity.LOW else None
            },
            original_exception=exception
        )
        
        # Log según severidad
        log_level = {
            ErrorSeverity.LOW: logging.DEBUG,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL
        }
        
        logger.log(
            log_level.get(severity, logging.ERROR),
            f"Error manejado: {error}",
            extra={"error_details": error.to_dict()}
        )
        
        return error
    
    @staticmethod
    def _build_message(
        exception: Exception,
        category: ErrorCategory,
        context: Dict[str, Any]
    ) -> str:
        """Construye mensaje descriptivo del error."""
        base_msg = str(exception)
        
        # Agregar contexto
        context_parts = []
        if "email" in context:
            context_parts.append(f"Email: {context['email']}")
        if "operation" in context:
            context_parts.append(f"Operación: {context['operation']}")
        if "folder" in context:
            context_parts.append(f"Carpeta: {context['folder']}")
        
        context_str = " | ".join(context_parts) if context_parts else ""
        
        # Mensajes específicos por categoría
        category_messages = {
            ErrorCategory.AUTHENTICATION: 
                f"Error de autenticación: {base_msg}. Verifica credenciales.",
            ErrorCategory.NETWORK: 
                f"Error de conexión: {base_msg}. Verifica tu conexión a internet.",
            ErrorCategory.RATE_LIMIT: 
                f"Límite de tasa excedido: {base_msg}. Espera antes de reintentar.",
            ErrorCategory.IMAP: 
                f"Error en servidor IMAP: {base_msg}. Intenta más tarde.",
            ErrorCategory.PARSING: 
                f"Error procesando correo: {base_msg}. El correo puede estar corrupto.",
            ErrorCategory.CONFIGURATION: 
                f"Error de configuración: {base_msg}. Revisa variables de entorno."
        }
        
        main_msg = category_messages.get(category, f"Error: {base_msg}")
        
        if context_str:
            main_msg += f" [Contexto: {context_str}]"
        
        return main_msg
    
    @staticmethod
    def is_recoverable_error(exception: Exception) -> bool:
        """Determina si un error es recuperable sin análisis profundo."""
        error = ErrorHandler.handle_exception(exception)
        return error.recoverable

# Funciones auxiliares para manejo rápido
def handle_imap_error(func):
    """Decorador para manejo automático de errores IMAP."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error = ErrorHandler.handle_exception(e, {
                "operation": func.__name__
            })
            raise error from e
    return wrapper

def safe_execute(func, *args, default=None, **kwargs):
    """Ejecuta función de forma segura, retornando valor por defecto en error."""
    try:
        return func(*args, **kwargs)
    except EmailRecoveryError as e:
        if not e.recoverable:
            logger.error(f"Error no recuperable en {func.__name__}: {e}")
        else:
            logger.warning(f"Error recuperable en {func.__name__}: {e}")
        return default
    except Exception as e:
        logger.error(f"Error inesperado en {func.__name__}: {e}")
        return default
