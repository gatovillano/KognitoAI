#!/usr/bin/env python3
"""
Script de debug para ver exactamente qué formato devuelve la búsqueda web.
"""

import asyncio
import sys
import os

# Agregar el directorio actual al path
sys.path.append('/app')

from tools.web_search_tool import get_web_search_tool

async def debug_search_format():
    """Prueba la búsqueda web y muestra el formato exacto de los resultados."""
    
    print("🔍 Iniciando debug de formato de búsqueda web...")
    
    # Crear la herramienta de búsqueda
    web_search_tool = get_web_search_tool()
    
    # Realizar una búsqueda simple
    query = "modelos ligeros de IA"
    print(f"📝 Consulta: {query}")
    
    try:
        # Ejecutar búsqueda con configuración mínima
        from langchain_core.runnables import RunnableConfig
        config = RunnableConfig()
        results = await web_search_tool._arun(query, config=config)
        
        print("\n" + "="*80)
        print("RESULTADOS COMPLETOS DE BÚSQUEDA:")
        print("="*80)
        print(results)
        print("="*80)
        
        # Buscar URLs manualmente
        import re
        
        print("\n🔍 ANÁLISIS DE EXTRACCIÓN DE URLs:")
        print("-" * 50)
        
        # Patrón 1: Markdown [Ver fuente completa](url)
        markdown_urls = re.findall(r"\[Ver fuente completa\]\((.*?)\)", results)
        print(f"📋 URLs en formato markdown: {len(markdown_urls)}")
        for i, url in enumerate(markdown_urls, 1):
            print(f"  {i}. {url}")
        
        # Patrón 2: HTML <a href='url'>
        html_urls = re.findall(r"<a href=\'(.*?)\'>", results)
        print(f"🌐 URLs en formato HTML: {len(html_urls)}")
        for i, url in enumerate(html_urls, 1):
            print(f"  {i}. {url}")
        
        # Patrón 3: Cualquier URL http/https
        all_urls = re.findall(r"https?://[^\s\)]+", results)
        print(f"🔗 Todas las URLs encontradas: {len(all_urls)}")
        for i, url in enumerate(all_urls, 1):
            print(f"  {i}. {url}")
        
        # Mostrar una muestra del texto para análisis manual
        print(f"\n📄 MUESTRA DEL TEXTO (primeros 1000 caracteres):")
        print("-" * 50)
        print(results[:1000])
        print("-" * 50)
        
        if len(results) > 1000:
            print(f"... (texto truncado, total: {len(results)} caracteres)")
        
    except Exception as e:
        print(f"❌ Error durante la búsqueda: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_search_format())
