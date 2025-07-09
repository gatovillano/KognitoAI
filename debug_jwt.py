#!/usr/bin/env python3
"""
Script de diagnóstico para problemas de JWT.
Ayuda a identificar problemas comunes con tokens JWT.
"""

import os
import jwt
import json
from datetime import datetime, timezone
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def debug_jwt_config():
    """Muestra la configuración actual de JWT."""
    print("=== CONFIGURACIÓN JWT ===")
    jwt_secret = os.getenv("JWT_SECRET_KEY", "supersecretkey")
    jwt_expiry = os.getenv("JWT_EXPIRY_DAYS", "7")
    
    print(f"JWT_SECRET_KEY: {jwt_secret[:10]}...{jwt_secret[-10:] if len(jwt_secret) > 20 else jwt_secret}")
    print(f"JWT_EXPIRY_DAYS: {jwt_expiry}")
    print(f"Longitud del secret: {len(jwt_secret)} caracteres")
    print()

def create_test_token():
    """Crea un token de prueba con la configuración actual."""
    print("=== CREANDO TOKEN DE PRUEBA ===")
    jwt_secret = os.getenv("JWT_SECRET_KEY", "supersecretkey")
    
    payload = {
        "sub": "test-account-id",
        "exp": datetime.now(timezone.utc).timestamp() + (7 * 24 * 60 * 60),  # 7 días
        "iat": datetime.now(timezone.utc).timestamp()
    }
    
    token = jwt.encode(payload, jwt_secret, algorithm="HS256")
    print(f"Token creado: {token[:50]}...")
    print()
    return token

def verify_test_token(token):
    """Verifica un token con la configuración actual."""
    print("=== VERIFICANDO TOKEN DE PRUEBA ===")
    jwt_secret = os.getenv("JWT_SECRET_KEY", "supersecretkey")
    
    try:
        payload = jwt.decode(token, jwt_secret, algorithms=["HS256"])
        print("✅ Token verificado correctamente")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        return True
    except jwt.ExpiredSignatureError:
        print("❌ Token expirado")
        return False
    except jwt.InvalidSignatureError:
        print("❌ Firma inválida - el secret key no coincide")
        return False
    except jwt.PyJWTError as e:
        print(f"❌ Error de JWT: {e}")
        return False

def analyze_token_without_verification(token):
    """Analiza un token sin verificar la firma."""
    print("=== ANÁLISIS SIN VERIFICACIÓN ===")
    try:
        # Decodificar sin verificar
        payload = jwt.decode(token, options={"verify_signature": False})
        print("Payload del token (sin verificar firma):")
        print(json.dumps(payload, indent=2))
        
        # Verificar expiración
        if 'exp' in payload:
            exp_time = datetime.fromtimestamp(payload['exp'], tz=timezone.utc)
            now = datetime.now(timezone.utc)
            print(f"Expira: {exp_time}")
            print(f"Ahora: {now}")
            if exp_time > now:
                print("✅ Token no expirado")
            else:
                print("❌ Token expirado")
        
    except Exception as e:
        print(f"Error analizando token: {e}")

if __name__ == "__main__":
    print("🔍 DIAGNÓSTICO JWT\n")
    
    # Mostrar configuración
    debug_jwt_config()
    
    # Crear y verificar token de prueba
    test_token = create_test_token()
    verify_test_token(test_token)
    
    print("\n" + "="*50)
    print("Para probar con un token específico, ejecuta:")
    print("python debug_jwt.py <token>")
    
    # Si se proporciona un token como argumento
    import sys
    if len(sys.argv) > 1:
        provided_token = sys.argv[1]
        print(f"\n=== ANALIZANDO TOKEN PROPORCIONADO ===")
        print(f"Token: {provided_token[:50]}...")
        analyze_token_without_verification(provided_token)
        verify_test_token(provided_token)
