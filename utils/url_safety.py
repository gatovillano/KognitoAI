"""
Validación de URLs salientes para mitigar SSRF en endpoints que aceptan api_base.
"""

from __future__ import annotations

import ipaddress
import socket
from typing import Iterable
from urllib.parse import urlparse

# Proveedores donde apuntar a hosts privados/locales es un caso de uso legítimo (Ollama, vLLM, etc.)
_LOCAL_NETWORK_PROVIDERS = frozenset(
    {
        "ollama",
        "ollama_cloud",
        "ollama-cloud",
        "openai_compatible",
        "openai-compatible",
    }
)

_BLOCKED_HOSTNAMES = frozenset(
    {
        "metadata.google.internal",
        "metadata.goog",
        "169.254.169.254",
    }
)

_LINK_LOCAL_NETWORK = ipaddress.ip_network("169.254.0.0/16")


SAFE_HTTPX_CLIENT_OPTIONS = {"follow_redirects": False}


class SSRFValidationError(ValueError):
    """La URL no es segura para una petición HTTP saliente desde el servidor."""


def _normalize_provider(provider: str) -> str:
    return provider.lower().replace("-", "_")


def _provider_allows_private_network(provider: str) -> bool:
    return _normalize_provider(provider) in _LOCAL_NETWORK_PROVIDERS


def _hostname_is_blocked(hostname: str) -> bool:
    host = hostname.strip().lower().rstrip(".")
    if not host:
        return True
    if host in _BLOCKED_HOSTNAMES:
        return True
    if host.endswith(".internal") or host.endswith(".local"):
        return True
    return False


def _ip_is_link_local(ip: ipaddress._BaseAddress) -> bool:
    if ip.is_link_local:
        return True
    try:
        return ip in _LINK_LOCAL_NETWORK
    except TypeError:
        return False


def _ip_is_disallowed_for_provider(
    ip: ipaddress._BaseAddress, allow_private_network: bool
) -> bool:
    if _ip_is_link_local(ip):
        return True
    if ip.is_multicast or ip.is_reserved or ip.is_unspecified:
        return True
    if not allow_private_network:
        if ip.is_private or ip.is_loopback:
            return True
    return False


def _resolve_host_ips(hostname: str) -> Iterable[ipaddress._BaseAddress]:
    try:
        addr_infos = socket.getaddrinfo(
            hostname, None, type=socket.SOCK_STREAM
        )
    except socket.gaierror as exc:
        raise SSRFValidationError(f"No se pudo resolver el host '{hostname}'.") from exc

    ips: list[ipaddress._BaseAddress] = []
    for family, _, _, _, sockaddr in addr_infos:
        if family == socket.AF_INET:
            ips.append(ipaddress.ip_address(sockaddr[0]))
        elif family == socket.AF_INET6:
            ips.append(ipaddress.ip_address(sockaddr[0]))

    if not ips:
        raise SSRFValidationError(f"No se encontraron direcciones para '{hostname}'.")

    return ips


def _validate_resolved_ips(
    ips: Iterable[ipaddress._BaseAddress], allow_private_network: bool
) -> None:
    for ip in ips:
        if _ip_is_disallowed_for_provider(ip, allow_private_network):
            raise SSRFValidationError(
                "La URL apunta a una red o dirección no permitida para este proveedor."
            )


def validate_llm_api_base(url: str, provider: str) -> str:
    """
    Valida que una api_base sea segura antes de usarla en peticiones HTTP del servidor.

    - Solo permite esquemas http/https.
    - Bloquea credenciales embebidas en la URL.
    - Resuelve DNS y rechaza IPs de metadatos, link-local y (según proveedor) redes privadas.
    """
    cleaned = (url or "").strip()
    if not cleaned:
        raise SSRFValidationError("api_base no puede estar vacía.")

    parsed = urlparse(cleaned)
    if parsed.scheme not in {"http", "https"}:
        raise SSRFValidationError("api_base debe usar esquema http o https.")

    if parsed.username or parsed.password:
        raise SSRFValidationError("api_base no puede incluir credenciales en la URL.")

    hostname = parsed.hostname
    if not hostname:
        raise SSRFValidationError("api_base debe incluir un host válido.")

    if _hostname_is_blocked(hostname):
        raise SSRFValidationError("El host de api_base no está permitido.")

    allow_private = _provider_allows_private_network(provider)

    # IP literal en el host (ej. http://10.0.0.5:11434)
    try:
        literal_ip = ipaddress.ip_address(hostname)
    except ValueError:
        literal_ip = None

    if literal_ip is not None:
        _validate_resolved_ips([literal_ip], allow_private)
    else:
        _validate_resolved_ips(_resolve_host_ips(hostname), allow_private)

    return cleaned.rstrip("/")


def require_safe_llm_api_base(url: Optional[str], provider: str) -> Optional[str]:
    """
    Valida api_base procedente de configuración de usuario/admin.
    Devuelve None si la URL está vacía.
    """
    cleaned = (url or "").strip()
    if not cleaned:
        return None
    return validate_llm_api_base(cleaned, provider)
