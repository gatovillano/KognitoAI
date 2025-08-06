#!/usr/bin/env python3
"""
Script para probar directamente la herramienta comprehensive_web_analysis_tool.
"""

import asyncio
import sys
import os

# Agregar el directorio actual al path
sys.path.append('/app')

from tools.comprehensive_web_analysis_tool import ComprehensiveWebAnalysisTool

async def test_comprehensive_tool():
    """Prueba la herramienta de análisis web comprehensivo."""
    
    print("🔍 Iniciando prueba de herramienta comprehensive_web_analysis...")
    
    # Crear la herramienta
    account_id = "test-account-123"
    tool = ComprehensiveWebAnalysisTool(account_id=account_id)
    
    # Realizar análisis
    query = "modelos ligeros de IA"
    print(f"📝 Consulta: {query}")
    
    try:
        # Ejecutar análisis
        from langchain_core.runnables import RunnableConfig
        config = RunnableConfig()
        
        print("🚀 Ejecutando análisis comprehensivo...")
        results = await tool._arun(query=query, config=config)
        
        print("\n" + "="*80)
        print("RESULTADOS DEL ANÁLISIS COMPREHENSIVO:")
        print("="*80)
        print(results)
        print("="*80)
        
    except Exception as e:
        print(f"❌ Error durante el análisis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_comprehensive_tool())
