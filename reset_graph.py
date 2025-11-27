import sys
import os
import asyncio
import requests

# Script para limpiar Neo4j y reprocesar el grafo

async def main():
    # URL del backend
    base_url = "http://localhost:8889"
    
    # Token de autenticación (deberías obtenerlo del usuario real)
    # Por ahora, vamos a usar el endpoint de test que no requiere auth
    
    print("🧹 Paso 1: Limpiando Neo4j...")
    try:
        response = requests.post(f"{base_url}/clear-neo4j")
        if response.status_code == 200:
            print("✅ Neo4j limpiado exitosamente")
            print(response.json())
        else:
            print(f"❌ Error limpiando Neo4j: {response.status_code}")
            print(response.text)
            return
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    print("\n📊 Paso 2: Verificando estado...")
    try:
        response = requests.post(f"{base_url}/test-neo4j-connection")
        if response.status_code == 200:
            print("✅ Conexión verificada")
            print(response.json())
        else:
            print(f"⚠️ Advertencia: {response.status_code}")
    except Exception as e:
        print(f"⚠️ Advertencia: {e}")
    
    print("\n🔄 Paso 3: Reprocesando grafo...")
    print("Nota: Necesitarás ejecutar el procesamiento desde el frontend con tu cuenta de usuario")
    print("Ve a la sección de Knowledge Graph y presiona 'Procesar Documentos'")

if __name__ == "__main__":
    asyncio.run(main())
