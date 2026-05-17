---
name: template-skill
description: |
  Plantilla reutilizable para crear nuevas skills siguiendo agentskills.io.
  Copia este archivo y adapta los valores para tu skill específica.
license: MIT
compatibility: Python 3.10+, requires async runtime
metadata:
  author: KognitoAI Team
  version: "1.0.0"
  template: true
  tags:
    - template
    - example
  category: development-tools
allowed-tools: |
  filesystem__read_file
  filesystem__write_file
---

# Template Skill

## Descripción Corta
Una línea clara de qué hace este skill.

## Descripción Completa
Párrafo más detallado explicando:
- Qué problema resuelve
- Cuáles son sus capacidades principales
- Limitaciones importantes

## Cuándo Usarlo

Usa este skill cuando:
- Necesites [situación específica]
- Quieras [objetivo específico]
- Tengas acceso a [recursos necesarios]

**No uses este skill si:**
- Necesitas [algo fuera del scope]
- No tienes acceso a [recurso requerido]

## Cómo Usarlo

### Instalación / Setup (si aplica)
```bash
# Comando para configurar el skill
pip install requirement
```

### Uso Básico
```python
# Importar el skill
from skills.template_skill import template_function

# Llamada básica
result = await template_function(param1="value")
print(result)
```

### Parámetros

| Parámetro | Tipo | Requerido | Descripción |
|---|---|---|---|
| `param1` | str | Sí | Descripción del parámetro 1 |
| `param2` | int | No (default: 10) | Descripción del parámetro 2 |
| `param3` | list | No | Lista de opciones |

### Return Value
Devuelve: `dict` con las siguientes claves:
- `success` (bool): Indica si la operación fue exitosa
- `data` (any): Los datos resultantes
- `error` (str|null): Mensaje de error si aplica

### Ejemplos

#### Ejemplo 1: Uso Simple
```python
result = await template_function(param1="hello")
# Output: {"success": true, "data": "processed hello"}
```

#### Ejemplo 2: Con Parámetros Adicionales
```python
result = await template_function(
    param1="data",
    param2=20,
    param3=["option1", "option2"]
)
# Output: {"success": true, "data": {...}}
```

#### Ejemplo 3: Manejo de Errores
```python
try:
    result = await template_function(param1="invalid")
    if not result["success"]:
        print(f"Error: {result['error']}")
    else:
        print(f"Success: {result['data']}")
except Exception as e:
    print(f"Exception: {e}")
```

## Composición con Otros Skills

Este skill funciona bien con:
- **[other-skill](../other-skill)** - Para [propósito específico]
- **[another-skill](../another-skill)** - Para [propósito específico]

### Patrón de Composición
```python
from skills.template_skill import template_function
from skills.other_skill import other_function

# Combinar skills
result1 = await template_function(param1="input")
result2 = await other_function(param1=result1["data"])
```

## Limitaciones y Casos de Borde

- **Limitación 1**: Descrición de limitación y workaround
- **Limitación 2**: Descripción de limitación y workaround

### Manejo de Casos de Borde

1. **Entrada vacía**
   - Comportamiento: Devuelve error "Parameter cannot be empty"
   - Workaround: Validar entrada antes de llamar

2. **Timeout**
   - Comportamiento: Lanza excepción después de 30s
   - Workaround: Implementar retry logic

## Solución de Problemas

### Problema: Error "Connection Failed"
**Solución:**
1. Verificar conectividad de red
2. Validar credenciales de API (si aplica)
3. Revisar logs en `logs/template_skill.log`

### Problema: Resultados inesperados
**Solución:**
1. Revisar los parámetros de entrada
2. Consultar [Debugging Guide](references/debugging.md)
3. Ejecutar con `debug=True` para verbose output

## Referencias

Para información más detallada, ver:
- [Technical Reference](references/REFERENCE.md) - Detalles de implementación
- [API Documentation](references/api-reference.md) - Especificación completa
- [Examples](references/examples.md) - Casos de uso avanzados
- [Troubleshooting](references/troubleshooting.md) - Problemas comunes

## Notas para Desarrolladores

Este skill utiliza:
- **Lenguaje**: Python 3.10+
- **Dependencias**: Ver `requirements.txt`
- **Async/Await**: Sí, todas las funciones son async
- **Testing**: `pytest tests/test_template_skill.py`

Ver [README.md](README.md) para guía de desarrollo.

## Historial de Cambios

| Versión | Fecha | Cambios |
|---|---|---|
| 1.0.0 | 2026-05-15 | Release inicial |
