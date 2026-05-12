import logging
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from utils.security import PIISanitizer, decode_access_token

logger = logging.getLogger("audit_log")
logger.setLevel(logging.INFO)

# Configurar un handler específico para auditoría si es necesario
# Por ahora usaremos el logger principal pero con un prefijo claro

class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Intentar obtener el usuario del token (sin fallar si no hay token)
        user_id = "anonymous"
        auth_header = request.headers.get("Authorization")
        path = request.url.path

        # OnlyOffice puede enviar JWT firmados con otra clave para callbacks/descarga.
        # En esas rutas evitamos decodificar para no contaminar logs de auditoria.
        skip_auth_decode = (
            path.startswith("/api/onlyoffice/download/")
            or path.startswith("/api/onlyoffice/office-callback/")
        )

        if not skip_auth_decode and auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            payload = decode_access_token(token)
            if payload:
                user_id = payload.get("sub", "unknown")

        # Sanitizar path y query params para no loguear PII en la URL
        sanitized_path = PIISanitizer.sanitize(request.url.path)
        sanitized_query = PIISanitizer.sanitize(str(request.query_params))

        response = await call_next(request)
        
        process_time = time.time() - start_time
        
        # Loguear la petición (Auditoría)
        # Formato: [AUDIT] User: {user_id} | Method: {method} | Path: {path} | Status: {status} | Time: {time}s
        logger.info(
            f"[AUDIT] User: {user_id} | Method: {request.method} | "
            f"Path: {sanitized_path} | Query: {sanitized_query} | "
            f"Status: {response.status_code} | Time: {process_time:.4f}s"
        )
        
        return response