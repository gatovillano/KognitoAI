#!/usr/bin/env python3
"""
Prueba de conexión con API KAI
"""

import asyncio
import aiohttp
import json
import os

API_URL = "https://apibase.cuerpolibre.cl"
API_KEY = "bac65afb5234660a6490aefe3a01923713a904418e4f59b5fbb81d888e2d76cc"

async def test_query():
    """Prueba query a la API"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    async with aiohttp.ClientSession() as session:
        # Probar endpoint de health
        try:
            async with session.get(f"{API_URL}/health", headers=headers) as resp:
                health = await resp.json()
                print(f"Health check: {health}")
        except Exception as e:
            print(f"Error en health: {e}")
        
        # Probar query
        try:
            payload = {"query": "¿Qué es KAI?"}
            async with session.post(
                f"{API_URL}/api/v1/query",
                json=payload,
                headers=headers
            ) as resp:
                result = await resp.json()
                print(f"\nQuery result: {json.dumps(result, indent=2)}")
        except Exception as e:
            print(f"Error en query: {e}")

if __name__ == "__main__":
    asyncio.run(test_query())
