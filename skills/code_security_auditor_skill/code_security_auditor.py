"""
Skill de Auditoría de Seguridad de Código
Detecta vulnerabilidades y patrones peligrosos en código fuente.
"""

import re
import os
from pathlib import Path
from typing import Dict, List, Any, Optional

# Patrones de vulnerabilidades por lenguaje
SECURITY_PATTERNS = {
    "python": [
        {
            "name": "SQL Injection",
            "pattern": r"(execute|executemany|raw|extra|text)\s*\(\s*[\"'].*\{.*\}.*[\"']",
            "severity": "critical",
            "description": "Posible inyección SQL detectada. Usar parámetros con nombre o prepared statements."
        },
        {
            "name": "Command Injection",
            "pattern": r"os\.system|subprocess\.(call|run|Popen)\s*\([^)]*shell\s*=\s*True",
            "severity": "critical",
            "description": "Ejecución de comandos del sistema. Validar y sanitizar entradas."
        },
        {
            "name": "eval/exec",
            "pattern": r"\b(eval|exec)\s*\(",
            "severity": "critical",
            "description": "Uso de eval/exec es peligroso. Considerar alternativas seguras."
        },
        {
            "name": "Hardcoded Secret",
            "pattern": r"(password|secret|key|token|api_key|private_key)\s*=\s*[\"'][^\"']{8,}[\"']",
            "severity": "high",
            "description": "Secreto codificado en el código. Usar variables de entorno."
        },
        {
            "name": "Weak Crypto",
            "pattern": r"(md5|sha1)\s*\(",
            "severity": "medium",
            "description": "Algoritmo de hash débil. Usar SHA-256 o superior."
        },
        {
            "name": "Debug Mode",
            "pattern": r"DEBUG\s*=\s*True|debug\s*=\s*True|app\.debug\s*=\s*True",
            "severity": "high",
            "description": "Modo debug habilitado. Deshabilitar en producción."
        },
        {
            "name": "Insecure Deserialization",
            "pattern": r"pickle\.loads|yaml\.load\s*\([^)]*\)",
            "severity": "critical",
            "description": "Deserialización insegura. Usar json o yaml.safe_load."
        },
        {
            "name": "Path Traversal",
            "pattern": r"open\s*\(|read\s*\(|write\s*\(\s*[^)]*\+|os\.path\.join\s*\([^)]*\+",
            "severity": "high",
            "description": "Posible path traversal. Validar rutas de entrada."
        },
        {
            "name": "XSS Risk",
            "pattern": r"render_template_string|mark_safe|__html__|innerHTML\s*=",
            "severity": "high",
            "description": "Posible XSS. Sanitizar salidas HTML."
        },
        {
            "name": "Weak Password Hash",
            "pattern": r"hashlib\.sha1\s*\(|md5\s*\([^)]*password",
            "severity": "high",
            "description": "Hash de contraseña débil. Usar bcrypt o argon2."
        }
    ],
    "javascript": [
        {
            "name": "DOM XSS",
            "pattern": r"innerHTML|outerHTML\s*=",
            "severity": "high",
            "description": "Asignación directa a innerHTML. Sanitizar entrada."
        },
        {
            "name": "Eval",
            "pattern": r"\beval\s*\(",
            "severity": "critical",
            "description": "Uso de eval(). Muy peligroso."
        },
        {
            "name": "Hardcoded Secret",
            "pattern": r"API_KEY|SECRET|PASSWORD\s*:\s*[\"'][^\"']{8,}[\"']",
            "severity": "high",
            "description": "Secreto en código fuente."
        }
    ]
}


def get_severity_level(severity: str) -> int:
    """Convierte severidad a nivel numérico para filtrado."""
    levels = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    return levels.get(severity.lower(), 3)


def check_file(file_path: str, patterns: List[Dict], min_severity: str) -> List[Dict]:
    """Audita un archivo en busca de patrones de seguridad."""
    findings = []
    min_sev_level = get_severity_level(min_severity)
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            lines = content.split('\n')
            
        for pattern_info in patterns:
            if get_severity_level(pattern_info['severity']) > min_sev_level:
                continue
                
            matches = re.finditer(pattern_info['pattern'], content, re.IGNORECASE | re.MULTILINE)
            
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                line_content = lines[line_num - 1].strip()[:100]
                
                findings.append({
                    "file": file_path,
                    "line": line_num,
                    "severity": pattern_info['severity'],
                    "type": pattern_info['name'],
                    "description": pattern_info['description'],
                    "code_snippet": line_content,
                    "match": match.group()[:50]
                })
                
    except Exception as e:
        findings.append({
            "file": file_path,
            "error": str(e),
            "severity": "low",
            "type": "Read Error",
            "description": f"No se pudo leer el archivo: {e}"
        })
    
    return findings


def audit_code(path: str, file_types: List[str], severity: str, output_format: str) -> Dict[str, Any]:
    """Función principal de auditoría de código."""
    
    all_findings = []
    path_obj = Path(path)
    
    if not path_obj.exists():
        return {"error": f"La ruta {path} no existe", "findings": []}
    
    # Determinar archivos a auditar
    files_to_audit = []
    if path_obj.is_file():
        files_to_audit = [str(path_obj)]
    else:
        for ext in file_types:
            files_to_audit.extend(str(p) for p in path_obj.rglob(f"*.{ext}"))
    
    # Obtener patrones relevantes
    patterns = []
    for ft in file_types:
        if ft in SECURITY_PATTERNS:
            patterns.extend(SECURITY_PATTERNS[ft])
    
    # Auditar cada archivo
    for file_path in files_to_audit[:100]:  # Límite de rendimiento
        findings = check_file(file_path, patterns, severity)
        all_findings.extend(findings)
    
    # Generar estadísticas
    stats = {
        "total_files": len(files_to_audit),
        "total_findings": len(all_findings),
        "by_severity": {},
        "by_type": {}
    }
    
    for finding in all_findings:
        sev = finding.get('severity', 'unknown')
        stats['by_severity'][sev] = stats['by_severity'].get(sev, 0) + 1
        ftype = finding.get('type', 'unknown')
        stats['by_type'][ftype] = stats['by_type'].get(ftype, 0) + 1
    
    # Formatear salida
    if output_format == "json":
        return {"findings": all_findings, "statistics": stats}
    
    elif output_format == "markdown":
        report = ["# Informe de Auditoría de Seguridad\n"]
        report.append(f"**Resumen:** {stats['total_findings']} hallazgos en {stats['total_files']} archivos\n")
        
        report.append("## Estadísticas\n")
        report.append("| Severidad | Cantidad |")
        report.append("|-----------|----------|")
        for sev, count in stats['by_severity'].items():
            report.append(f"| {sev.upper()} | {count} |")
        
        if all_findings:
            report.append("\n## Hallazgos\n")
            for finding in all_findings[:50]:
                report.append(f"### {finding['type']} - {finding['severity'].upper()}")
                report.append(f"**Archivo:** `{finding['file']}` (línea {finding['line']})")
                report.append(f"**Descripción:** {finding['description']}")
                report.append(f"**Código:** `{finding['code_snippet']}`\n")
        
        return {"report": "\n".join(report), "findings": all_findings, "statistics": stats}
    
    else:  # text
        report_lines = [
            f"Auditoría de Seguridad - {stats['total_findings']} hallazgos en {stats['total_files']} archivos",
            "=" * 60
        ]
        for sev, count in stats['by_severity'].items():
            report_lines.append(f"  {sev.upper()}: {count}")
        return {"report": "\n".join(report_lines), "findings": all_findings, "statistics": stats}


async def run_audit(path: str, file_types: List[str] = None, severity: str = "medium", output_format: str = "markdown") -> Dict[str, Any]:
    """
    Audita código fuente en busca de vulnerabilidades de seguridad.
    
    Args:
        path: Ruta al archivo o directorio a auditar
        file_types: Tipos de archivos a auditar (python, js, ts, etc.)
        severity: Nivel mínimo de severidad (critical, high, medium, low)
        output_format: Formato de salida (json, markdown, text)
    """
    if file_types is None:
        file_types = ["python"]
    
    return audit_code(path, file_types, severity, output_format)