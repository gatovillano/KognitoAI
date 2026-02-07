# utils/onlyoffice_client.py

import logging
import httpx
import jwt
import time
from typing import Optional, Dict, Any
from core.config import settings

logger = logging.getLogger(__name__)

class OnlyOfficeClient:
    """
    Cliente robusto para interactuar con OnlyOffice Document Server.
    Implementa seguridad JWT, peticiones asíncronas y manejo de errores.
    """
    def __init__(self):
        self.url = getattr(settings, "onlyoffice_url", None)
        self.secret = getattr(settings, "onlyoffice_jwt_secret", None)
        self.enabled = bool(self.url)
        self.timeout = 30.0

    def is_available(self) -> bool:
        return self.enabled

    def _generate_token(self, payload: Dict[str, Any]) -> str:
        """Genera un token JWT para peticiones salientes."""
        if not self.secret:
            return ""
        # OnlyOffice espera que el payload esté dentro de una clave 'payload' a veces, 
        # pero para el editor config suele ser directo. Para Conversion API es directo.
        return jwt.encode(payload, self.secret, algorithm="HS256")

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verifica un token JWT recibido de OnlyOffice."""
        if not self.secret:
            logger.warning("🔑 [OnlyOffice] Intento de verificación sin secret configurado.")
            return None
        try:
            # OnlyOffice suele enviar el payload directo o dentro de una clave específica.
            # Verificamos y decodificamos.
            decoded = jwt.decode(token, self.secret, algorithms=["HS256"])
            # El payload real puede estar en 'payload' si viene de OnlyOffice Document Server
            if "payload" in decoded:
                return decoded["payload"]
            return decoded
        except jwt.ExpiredSignatureError:
            logger.error("🔑 [OnlyOffice] Token de callback expirado.")
        except jwt.InvalidTokenError as e:
            logger.error(f"🔑 [OnlyOffice] Token de callback inválido: {e}")
        except Exception as e:
            logger.error(f"🔑 [OnlyOffice] Error verificando token: {e}")
        return None

    async def convert_document(self, file_url: str, from_ext: str, to_ext: str = "docx") -> Optional[str]:
        """
        Solicita la conversión de un documento a OnlyOffice de forma asíncrona.
        De forma predeterminada convierte a docx para edición.
        """
        if not self.enabled:
            logger.warning("🚫 [OnlyOffice] Cliente no configurado.")
            return None

        conversion_url = f"{self.url.rstrip('/')}/ConvertService.ashx"
        
        # El 'key' debe ser único para el documento y su versión. 
        # Si queremos forzar reconversión, usamos el timestamp.
        payload = {
            "async": False,
            "filetype": from_ext.replace(".", ""),
            "key": f"conv_{int(time.time())}",
            "outputtype": to_ext,
            "url": file_url,
        }

        headers = {"Accept": "application/json"}
        if self.secret:
            token = self._generate_token(payload)
            headers["Authorization"] = f"Bearer {token}"
            # Algunos servicios de OnlyOffice también buscan el token en el cuerpo
            payload["token"] = token

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(conversion_url, json=payload, headers=headers)
                response.raise_for_status()
                result = response.json()
                
                if result.get("endConvert"):
                    return result.get("fileUrl")
                else:
                    error_code = result.get("error")
                    logger.error(f"❌ [OnlyOffice] Error en conversión (Código {error_code}): {result}")
                    return None
        except httpx.HTTPError as e:
            logger.error(f"🌐 [OnlyOffice] Error de conexión en conversión: {e}")
            return None
        except Exception as e:
            logger.error(f"⚠️ [OnlyOffice] Error inesperado en conversión: {e}")
            return None

    async def download_file(self, url: str) -> Optional[bytes]:
        """Descarga un archivo desde una URL (usado para recuperar archivos convertidos o guardados)."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.content
        except Exception as e:
            logger.error(f"📥 [OnlyOffice] Error descargando archivo desde {url}: {e}")
            return None

onlyoffice_client = OnlyOfficeClient()
