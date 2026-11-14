#!/usr/bin/env python3
"""
Script de prueba para verificar la conexión IMAP.
 Uso: python test_connection.py
"""

import os
import sys
from pathlib import Path

# Añadir directorio de scripts al path
sys.path.insert(0, str(Path(__file__).parent / "scripts"))

from secure_email_recovery import EmailRecovery
from error_handler import ErrorHandler

def test_disroot():
    """Prueba de conexión a Disroot."""
    print("\n" + "="*60)
    print("🧪 PRUEBA DE CONEXIÓN A DISROOT")
    print("="*60)
    
    # Cargar variables de entorno
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("⚠️  python-dotenv no instalado, usando variables de entorno del sistema")
    
    email = os.getenv("DISROOT_EMAIL_ADDRESS") or input("📧 Ingresa tu email de Disroot: ")
    password = os.getenv("DISROOT_EMAIL_PASSWORD")
    
    if not password or password == "tu_contraseña_aqui":
        print("⚠️  DISROOT_EMAIL_PASSWORD no configurada en .env")
        password = input("🔑 Ingresa tu contraseña de aplicación: ")
    
    print(f"\n📡 Conectando a disroot.org:993...")
    
    try:
        client = EmailRecovery(
            provider="disroot",
            email=email,
            password=password
        )
        
        # Validar configuración
        validation = client.validate_configuration()
        if not validation["valid"]:
            print(f"❌ Configuración inválida: {validation['issues']}")
            return False
        
        # Conectar y probar
        with client:
            # Probar listado de carpetas
            folders = client.get_folders()
            print(f"\n✅ Conectado exitosamente!")
            print(f"📁 Carpetas encontradas: {len(folders)}")
            for f in folders[:5]:  # Mostrar primeras 5
                print(f"   • {f['name']}")
            
            # Probar conteo de no leídos
            unread = client.get_unread_count()
            print(f"\n📬 Emails no leídos: {unread}")
            
            # Probar obtención de emails recientes (limitado a 3 para prueba)
            print(f"\n📨 Obteniendo 3 emails recientes...")
            emails = client.get_recent_emails(limit=3)
            
            if emails:
                print(f"✅ Obtenidos {len(emails)} emails:")
                for i, email in enumerate(emails[:3], 1):
                    print(f"\n   [{i}] {email.subject}")
                    print(f"       De: {email.from_addr}")
                    print(f"       Fecha: {email.date.strftime('%Y-%m-%d %H:%M') if email.date else 'N/A'}")
            else:
                print("📭 No hay emails en la bandeja de entrada")
            
            # Estadísticas de caché
            if client.cache:
                stats = client.get_cache_stats()
                print(f"\n📊 Estadísticas de caché:")
                print(f"   Entradas: {stats['entries']}")
                print(f"   Hits: {stats['hits']}")
                print(f"   Misses: {stats['misses']}")
                print(f"   Hit rate: {stats['hit_rate_percent']:.1f}%")
        
        print("\n" + "="*60)
        print("✅ TODAS LAS PRUEBAS PASARON")
        print("="*60)
        return True
        
    except Exception as e:
        error = ErrorHandler.handle_exception(e, {"operation": "test_connection"})
        print(f"\n❌ ERROR: {error}")
        print(f"Categoría: {error.category.value}")
        print(f"Severidad: {error.severity.value}")
        if error.details.get("traceback"):
            print(f"\nTraceback:\n{error.details['traceback']}")
        return False

if __name__ == "__main__":
    success = test_disroot()
    sys.exit(0 if success else 1)
