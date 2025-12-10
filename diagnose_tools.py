#!/usr/bin/env python3
"""
Script de diagnóstico para verificar cómo se están formateando las herramientas
para diferentes LLMs a través de LiteLLM.
"""

import asyncio
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, '/home/gato/KognitoAI/kognito-ai')

from core.tools import get_all_langchain_tools
from core.llm_manager import get_main_llm
from core.config import settings
import json

async def diagnose_tool_binding():
    """Diagnostica cómo se están vinculando las herramientas al LLM."""
    
    print("🔍 Diagnóstico de Binding de Herramientas\n")
    print("=" * 60)
    
    # 1. Obtener el LLM configurado
    llm = get_main_llm()
    if not llm:
        print("❌ No se pudo obtener el LLM")
        return
    
    model_name = getattr(llm, 'model', 'unknown')
    print(f"\n📱 Modelo configurado: {model_name}")
    print(f"   Tipo de LLM: {type(llm).__name__}")
    
    # 2. Obtener las herramientas
    print("\n🔧 Obteniendo herramientas...")
    tools = await get_all_langchain_tools(
        account_id="test-account-id",
        telegram_id=None
    )
    
    print(f"   Total de herramientas: {len(tools)}")
    
    # 3. Encontrar web_search
    web_search_tool = None
    for tool in tools:
        if tool.name == "web_search":
            web_search_tool = tool
            break
    
    if not web_search_tool:
        print("❌ No se encontró la herramienta web_search")
        return
    
    print(f"\n🔎 Herramienta web_search encontrada:")
    print(f"   Nombre: {web_search_tool.name}")
    print(f"   Descripción (primeros 100 chars): {web_search_tool.description[:100]}...")
    
    # 4. Verificar el schema de argumentos
    if hasattr(web_search_tool, 'args_schema') and web_search_tool.args_schema:
        print(f"\n📋 Schema de argumentos:")
        schema = web_search_tool.args_schema.model_json_schema()
        print(json.dumps(schema, indent=2, ensure_ascii=False))
        
        # Verificar campos requeridos
        required_fields = schema.get('required', [])
        print(f"\n✅ Campos requeridos: {required_fields}")
        
        # Verificar propiedades
        properties = schema.get('properties', {})
        print(f"\n📝 Propiedades:")
        for prop_name, prop_info in properties.items():
            print(f"   - {prop_name}: {prop_info.get('type', 'unknown')} - {prop_info.get('description', 'sin descripción')[:50]}...")
    
    # 5. Intentar vincular herramientas al LLM
    print(f"\n🔗 Intentando vincular herramientas al LLM...")
    try:
        llm_with_tools = llm.bind_tools([web_search_tool])
        print("   ✅ Herramientas vinculadas exitosamente")
        
        # Verificar si el LLM tiene información sobre las herramientas vinculadas
        if hasattr(llm_with_tools, 'kwargs'):
            print(f"\n🔍 Kwargs del LLM con herramientas:")
            # Filtrar solo las claves relacionadas con tools
            tool_related_keys = [k for k in llm_with_tools.kwargs.keys() if 'tool' in k.lower()]
            for key in tool_related_keys:
                value = llm_with_tools.kwargs[key]
                if isinstance(value, (list, dict)):
                    print(f"   {key}:")
                    print(f"   {json.dumps(value, indent=4, ensure_ascii=False, default=str)[:500]}...")
                else:
                    print(f"   {key}: {value}")
        
    except AttributeError as e:
        print(f"   ❌ El LLM no soporta bind_tools: {e}")
    except Exception as e:
        print(f"   ❌ Error al vincular herramientas: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Diagnóstico completado")

if __name__ == "__main__":
    asyncio.run(diagnose_tool_binding())
