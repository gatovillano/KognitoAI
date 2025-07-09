#!/usr/bin/env python3
"""
🔬 Analizador de Estructura de Prompts
=====================================

Script para analizar y mostrar la estructura exacta de los prompts enviados al LLM,
incluyendo desglose de componentes, longitud, y análisis de contenido.

Uso:
    python scripts/prompt_structure_analyzer.py [opciones]

Ejemplos:
    # Análisis en tiempo real
    python scripts/prompt_structure_analyzer.py

    # Análisis de archivo de log específico
    python scripts/prompt_structure_analyzer.py --log-file logs/llm.log

    # Mostrar estadísticas detalladas
    python scripts/prompt_structure_analyzer.py --stats

    # Exportar análisis a JSON
    python scripts/prompt_structure_analyzer.py --export analysis.json
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import defaultdict, Counter
import subprocess

class PromptStructureAnalyzer:
    def __init__(self, 
                 show_stats: bool = False,
                 export_file: Optional[str] = None,
                 log_file: Optional[str] = None):
        self.show_stats = show_stats
        self.export_file = export_file
        self.log_file = log_file
        self.prompts_analyzed = []
        self.stats = defaultdict(int)
        self.component_stats = defaultdict(list)
    
    def _extract_prompt_components(self, prompt_content: str) -> Dict[str, Any]:
        """Extrae y analiza los componentes del prompt."""
        components = {
            'total_length': len(prompt_content),
            'total_lines': len(prompt_content.split('\n')),
            'sections': [],
            'react_components': {},
            'message_types': [],
            'tools_mentioned': [],
            'system_prompt_length': 0,
            'user_query_length': 0,
            'chat_history_length': 0
        }
        
        lines = prompt_content.split('\n')
        current_section = None
        current_content = []
        
        for line in lines:
            # Detectar secciones marcadas con ---
            section_match = re.match(r'^--- (.+) ---$', line.strip())
            if section_match:
                # Guardar sección anterior si existe
                if current_section:
                    components['sections'].append({
                        'name': current_section,
                        'content': '\n'.join(current_content),
                        'length': len('\n'.join(current_content)),
                        'lines': len(current_content)
                    })
                
                current_section = section_match.group(1)
                current_content = []
                continue
            
            if current_section:
                current_content.append(line)
            
            # Detectar componentes ReAct
            if line.strip().startswith('Question:'):
                components['react_components']['question'] = line.strip()[9:].strip()
            elif line.strip().startswith('Thought:'):
                components['react_components']['thought'] = line.strip()[8:].strip()
            elif line.strip().startswith('Action:'):
                components['react_components']['action'] = line.strip()[7:].strip()
            elif line.strip().startswith('Observation:'):
                components['react_components']['observation'] = line.strip()[12:].strip()
            
            # Detectar tipos de mensaje
            if re.search(r'(System:|Human:|Assistant:)', line):
                msg_type = re.search(r'(System|Human|Assistant):', line).group(1)
                components['message_types'].append(msg_type)
            
            # Detectar herramientas mencionadas
            tool_matches = re.findall(r'(\w+_tool|\w+Tool)', line)
            components['tools_mentioned'].extend(tool_matches)
        
        # Guardar última sección
        if current_section and current_content:
            components['sections'].append({
                'name': current_section,
                'content': '\n'.join(current_content),
                'length': len('\n'.join(current_content)),
                'lines': len(current_content)
            })
        
        # Calcular longitudes específicas
        for section in components['sections']:
            if 'sistema' in section['name'].lower() or 'system' in section['name'].lower():
                components['system_prompt_length'] += section['length']
            elif 'usuario' in section['name'].lower() or 'consulta' in section['name'].lower():
                components['user_query_length'] += section['length']
            elif 'historial' in section['name'].lower() or 'history' in section['name'].lower():
                components['chat_history_length'] += section['length']
        
        # Limpiar duplicados
        components['tools_mentioned'] = list(set(components['tools_mentioned']))
        
        return components
    
    def _analyze_prompt_complexity(self, components: Dict[str, Any]) -> Dict[str, Any]:
        """Analiza la complejidad del prompt."""
        complexity = {
            'score': 0,
            'factors': [],
            'category': 'simple'
        }
        
        # Factor: Longitud total
        if components['total_length'] > 5000:
            complexity['score'] += 3
            complexity['factors'].append('Muy largo (>5000 chars)')
        elif components['total_length'] > 2000:
            complexity['score'] += 2
            complexity['factors'].append('Largo (>2000 chars)')
        elif components['total_length'] > 1000:
            complexity['score'] += 1
            complexity['factors'].append('Mediano (>1000 chars)')
        
        # Factor: Número de secciones
        if len(components['sections']) > 5:
            complexity['score'] += 2
            complexity['factors'].append(f"Muchas secciones ({len(components['sections'])})")
        elif len(components['sections']) > 3:
            complexity['score'] += 1
            complexity['factors'].append(f"Varias secciones ({len(components['sections'])})")
        
        # Factor: Herramientas
        if len(components['tools_mentioned']) > 3:
            complexity['score'] += 2
            complexity['factors'].append(f"Muchas herramientas ({len(components['tools_mentioned'])})")
        elif len(components['tools_mentioned']) > 0:
            complexity['score'] += 1
            complexity['factors'].append(f"Con herramientas ({len(components['tools_mentioned'])})")
        
        # Factor: Componentes ReAct
        if len(components['react_components']) > 2:
            complexity['score'] += 1
            complexity['factors'].append("Patrón ReAct complejo")
        
        # Determinar categoría
        if complexity['score'] >= 6:
            complexity['category'] = 'muy_complejo'
        elif complexity['score'] >= 4:
            complexity['category'] = 'complejo'
        elif complexity['score'] >= 2:
            complexity['category'] = 'moderado'
        else:
            complexity['category'] = 'simple'
        
        return complexity
    
    def _format_prompt_analysis(self, prompt_data: Dict[str, Any]) -> str:
        """Formatea el análisis de un prompt para mostrar."""
        components = prompt_data['components']
        complexity = prompt_data['complexity']
        timestamp = prompt_data['timestamp']
        session_info = prompt_data.get('session_info', {})
        
        output = []
        output.append(f"\n{'='*80}")
        output.append(f"🔬 ANÁLISIS DE PROMPT {timestamp}")
        
        if session_info:
            session_str = " | ".join([f"{k}: {v}" for k, v in session_info.items() if v])
            output.append(f"📋 Sesión: {session_str}")
        
        output.append(f"{'='*80}")
        
        # Estadísticas generales
        output.append(f"📊 ESTADÍSTICAS GENERALES:")
        output.append(f"   • Longitud total: {components['total_length']:,} caracteres")
        output.append(f"   • Líneas totales: {components['total_lines']:,}")
        output.append(f"   • Secciones: {len(components['sections'])}")
        output.append(f"   • Herramientas mencionadas: {len(components['tools_mentioned'])}")
        
        # Análisis de complejidad
        output.append(f"\n🎯 COMPLEJIDAD: {complexity['category'].upper()} (Score: {complexity['score']})")
        if complexity['factors']:
            output.append(f"   Factores: {', '.join(complexity['factors'])}")
        
        # Desglose por secciones
        if components['sections']:
            output.append(f"\n📑 SECCIONES DETECTADAS:")
            for i, section in enumerate(components['sections'], 1):
                percentage = (section['length'] / components['total_length']) * 100
                output.append(f"   {i}. {section['name']}")
                output.append(f"      └─ {section['length']:,} chars ({percentage:.1f}%) | {section['lines']} líneas")
        
        # Componentes ReAct
        if components['react_components']:
            output.append(f"\n🤖 COMPONENTES REACT:")
            for comp_type, content in components['react_components'].items():
                preview = content[:100] + "..." if len(content) > 100 else content
                output.append(f"   • {comp_type.title()}: {preview}")
        
        # Herramientas
        if components['tools_mentioned']:
            output.append(f"\n🔧 HERRAMIENTAS MENCIONADAS:")
            output.append(f"   {', '.join(components['tools_mentioned'])}")
        
        # Tipos de mensaje
        if components['message_types']:
            msg_counts = Counter(components['message_types'])
            output.append(f"\n💬 TIPOS DE MENSAJE:")
            for msg_type, count in msg_counts.items():
                output.append(f"   • {msg_type}: {count}")
        
        return '\n'.join(output)
    
    def _update_stats(self, components: Dict[str, Any], complexity: Dict[str, Any]):
        """Actualiza las estadísticas globales."""
        self.stats['total_prompts'] += 1
        self.stats['total_characters'] += components['total_length']
        self.stats['total_lines'] += components['total_lines']
        self.stats['total_sections'] += len(components['sections'])
        self.stats[f"complexity_{complexity['category']}"] += 1
        
        # Estadísticas de componentes
        self.component_stats['lengths'].append(components['total_length'])
        self.component_stats['sections_count'].append(len(components['sections']))
        self.component_stats['tools_count'].append(len(components['tools_mentioned']))
        
        for tool in components['tools_mentioned']:
            self.stats[f"tool_{tool}"] += 1
    
    def _show_global_stats(self):
        """Muestra estadísticas globales del análisis."""
        if self.stats['total_prompts'] == 0:
            print("📊 No hay prompts analizados para mostrar estadísticas.")
            return
        
        print(f"\n{'='*60}")
        print(f"📊 ESTADÍSTICAS GLOBALES DEL ANÁLISIS")
        print(f"{'='*60}")
        
        print(f"📈 RESUMEN GENERAL:")
        print(f"   • Total de prompts analizados: {self.stats['total_prompts']}")
        print(f"   • Caracteres totales: {self.stats['total_characters']:,}")
        print(f"   • Promedio por prompt: {self.stats['total_characters'] // self.stats['total_prompts']:,} chars")
        print(f"   • Líneas totales: {self.stats['total_lines']:,}")
        print(f"   • Secciones totales: {self.stats['total_sections']}")
        
        print(f"\n🎯 DISTRIBUCIÓN DE COMPLEJIDAD:")
        complexity_types = ['simple', 'moderado', 'complejo', 'muy_complejo']
        for comp_type in complexity_types:
            count = self.stats.get(f"complexity_{comp_type}", 0)
            percentage = (count / self.stats['total_prompts']) * 100 if self.stats['total_prompts'] > 0 else 0
            print(f"   • {comp_type.title()}: {count} ({percentage:.1f}%)")
        
        # Top herramientas
        tool_stats = {k: v for k, v in self.stats.items() if k.startswith('tool_')}
        if tool_stats:
            print(f"\n🔧 HERRAMIENTAS MÁS USADAS:")
            sorted_tools = sorted(tool_stats.items(), key=lambda x: x[1], reverse=True)[:5]
            for tool_key, count in sorted_tools:
                tool_name = tool_key.replace('tool_', '')
                print(f"   • {tool_name}: {count} veces")
    
    def analyze_from_logs(self, log_source):
        """Analiza prompts desde logs (archivo o stream)."""
        print("🔬 Analizador de Estructura de Prompts")
        print("=" * 40)
        print(f"⏰ Iniciado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 40)
        
        try:
            if self.log_file:
                # Leer desde archivo
                print(f"📁 Analizando archivo: {self.log_file}")
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        self._process_log_line(line.strip())
            else:
                # Leer desde journalctl en tiempo real
                print("🔄 Analizando logs en tiempo real...")
                cmd = ["journalctl", "-f", "--no-pager", "-o", "cat"]
                
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
                
                while True:
                    line = process.stdout.readline()
                    if line:
                        self._process_log_line(line.strip())
                        
        except KeyboardInterrupt:
            print("\n🛑 Análisis detenido por el usuario")
        except Exception as e:
            print(f"❌ Error en el análisis: {e}")
        finally:
            if self.show_stats:
                self._show_global_stats()
            
            if self.export_file:
                self._export_analysis()
    
    def _process_log_line(self, line: str):
        """Procesa una línea de log buscando prompts."""
        if "📤 PROMPT ENVIADO AL LLM" in line and "Contenido:" in line:
            # Extraer información del prompt
            session_info = self._extract_session_info(line)
            
            # Extraer contenido del prompt
            content_match = re.search(r'Contenido: (.+)', line, re.DOTALL)
            if content_match:
                prompt_content = content_match.group(1)
                
                # Analizar componentes
                components = self._extract_prompt_components(prompt_content)
                complexity = self._analyze_prompt_complexity(components)
                
                prompt_data = {
                    'timestamp': datetime.now().strftime('%H:%M:%S'),
                    'session_info': session_info,
                    'components': components,
                    'complexity': complexity,
                    'raw_content': prompt_content
                }
                
                self.prompts_analyzed.append(prompt_data)
                self._update_stats(components, complexity)
                
                # Mostrar análisis
                print(self._format_prompt_analysis(prompt_data))
    
    def _extract_session_info(self, log_line: str) -> Dict[str, str]:
        """Extrae información de sesión del log."""
        session_info = {}
        
        account_match = re.search(r'Account: (\w+)', log_line)
        if account_match:
            session_info['account_id'] = account_match.group(1)
        
        thread_match = re.search(r'Thread: (\w+)', log_line)
        if thread_match:
            session_info['thread_id'] = thread_match.group(1)
        
        model_match = re.search(r'Model: ([\w-]+)', log_line)
        if model_match:
            session_info['model'] = model_match.group(1)
        
        return session_info
    
    def _export_analysis(self):
        """Exporta el análisis a un archivo JSON."""
        export_data = {
            'analysis_timestamp': datetime.now().isoformat(),
            'stats': dict(self.stats),
            'prompts': self.prompts_analyzed
        }
        
        with open(self.export_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Análisis exportado a: {self.export_file}")

def main():
    parser = argparse.ArgumentParser(
        description="Analizador de estructura de prompts del LLM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--log-file",
        type=str,
        help="Archivo de log específico para analizar (en lugar de tiempo real)"
    )
    
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Mostrar estadísticas detalladas al final"
    )
    
    parser.add_argument(
        "--export",
        type=str,
        help="Exportar análisis a archivo JSON"
    )
    
    args = parser.parse_args()
    
    analyzer = PromptStructureAnalyzer(
        show_stats=args.stats,
        export_file=args.export,
        log_file=args.log_file
    )
    
    analyzer.analyze_from_logs(args.log_file or "real-time")

if __name__ == "__main__":
    main()
