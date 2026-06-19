# Skill: Auditoría de Código

Audita código fuente en busca de vulnerabilidades de seguridad, patrones peligrosos y malas prácticas de programación.

## Parámetros

| Parámetro | Tipo | Requerido | Default | Descripción |
|-----------|------|-----------|---------|-------------|
| `path` | string | Sí | - | Ruta al archivo o directorio a auditar |
| `file_types` | array | No | `["python"]` | Tipos de archivos: `["python", "js", "ts", ...]` |
| `severity` | string | No | `"medium"` | Severidad mínima: `"critical"`, `"high"`, `"medium"`, `"low"` |
| `output_format` | string | No | `"markdown"` | Formato de salida: `"json"`, `"markdown"`, `"text"` |

## Ejemplos de Uso

```yaml
skill: code_security_auditor
parameters:
  path: "/home/gato/Proyectos/KognitoAI/kognito-ai/api"
  file_types: ["python"]
  severity: "high"
  output_format: "markdown"
```

## Hallazgos Detectados

### Python
- **SQL Injection**: Consultas SQL con interpolación de strings
- **Command Injection**: Uso de `os.system` o `subprocess` con `shell=True`
- **Code Injection**: Uso de `eval()` o `exec()`
- **Hardcoded Secrets**: Secrets codificados en el código
- **Debug Mode**: Modo debug habilitado en producción
- **Weak Cryptography**: Uso de MD5 o SHA1
- **Insecure Deserialization**: Uso de `pickle` o `yaml.load`
- **Path Traversal**: Rutas de archivo sin validar
- **XSS Risk**: Renderizado de HTML sin sanitizar
- **Weak Password Hash**: Hashes de contraseña débiles

### JavaScript
- **DOM XSS**: Asignación directa a `innerHTML`
- **Eval**: Uso de `eval()`
- **Hardcoded Secrets**: Secrets en código fuente

## Salidas

### JSON
```json
{
  "findings": [...],
  "statistics": {
    "total_files": 10,
    "total_findings": 5,
    "by_severity": {"high": 3, "medium": 2},
    "by_type": {"Hardcoded Secret": 2, "Debug Mode": 1}
  }
}
```

### Markdown
Reporte formateado con tabla de severidades y detalles de cada hallazgo.

## Consideraciones de Seguridad

⚠️ **Importante**: Esta skill detecta patrones, no analiza el contexto completo del código. Siempre verificar manualmente los hallazgos críticos.