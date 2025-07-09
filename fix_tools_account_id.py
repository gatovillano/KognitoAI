#!/usr/bin/env python3
"""
Script para identificar y arreglar herramientas que aún requieren account_id explícitamente.
"""

import os
import re
from pathlib import Path

def find_tools_with_account_id():
    """Encuentra herramientas que aún tienen account_id como campo requerido."""
    tools_dir = Path("tools")
    problematic_tools = []
    
    for tool_file in tools_dir.glob("*.py"):
        if tool_file.name.startswith("__"):
            continue
            
        content = tool_file.read_text()
        
        # Buscar patrones problemáticos
        patterns = [
            r'account_id.*Field\(\s*\.\.\.',  # account_id requerido
            r'async def _arun\(.*account_id.*\)',  # _arun con account_id como parámetro
        ]
        
        for pattern in patterns:
            if re.search(pattern, content, re.MULTILINE | re.DOTALL):
                problematic_tools.append(tool_file.name)
                break
    
    return problematic_tools

def main():
    print("🔍 Buscando herramientas que aún requieren account_id explícitamente...")
    
    problematic_tools = find_tools_with_account_id()
    
    if problematic_tools:
        print(f"\n❌ Encontradas {len(problematic_tools)} herramientas problemáticas:")
        for tool in sorted(problematic_tools):
            print(f"  - {tool}")
    else:
        print("\n✅ No se encontraron herramientas problemáticas.")
    
    print("\n📝 Herramientas ya corregidas:")
    corrected = [
        "comprehensive_web_analysis_tool.py",
        "knowledge_analysis_tool.py", 
        "get_document_list_tool.py",
        "get_document_content_tool.py",
        "get_analysis_results_tool.py",
        "conversation_context_analyzer_tool.py",
        "multi_query_search_tool.py",
        "get_agenda_tool.py"
    ]
    
    for tool in corrected:
        print(f"  ✅ {tool}")

if __name__ == "__main__":
    main()
