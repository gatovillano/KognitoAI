"""
Parser híbrido multi-estrategia para extraer tool calls del texto.
Basado en el sistema de Kogniterm que soporta múltiples formatos.

Estrategias:
A) Patrones explícitos: "LLAMADA_A_HERRAMIENTA: nombre"
B) Bloques JSON estructurados: {"name": "...", "args": {...}}
C) Formato legacy: nombre_herramienta({args})
"""

import json
import re
import uuid
from typing import Any, Dict, List, Optional


def _extract_balanced_json(text: str, start_idx: int) -> Optional[str]:
    """
    Extrae un bloque JSON balanceado comenzando desde start_idx.
    Retorna el string JSON completo o None si no está balanceado.
    """
    if start_idx >= len(text) or text[start_idx] != "{":
        return None

    depth = 0
    in_string = False
    escape_next = False

    for i in range(start_idx, len(text)):
        char = text[i]

        if escape_next:
            escape_next = False
            continue

        if char == "\\":
            escape_next = True
            continue

        if char == '"' and not escape_next:
            in_string = not in_string
            continue

        if not in_string:
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[start_idx : i + 1]

    return None


def parse_tool_calls_from_text(
    text: str, available_tools: List[Any]
) -> List[Dict[str, Any]]:
    """
    Parser híbrido multi-estrategia para extraer tool calls del texto.
    Basado en el sistema de Kogniterm que soporta múltiples formatos.

    Estrategias:
    A) Patrones explícitos: "LLAMADA_A_HERRAMIENTA: nombre"
    B) Bloques JSON estructurados: {"name": "...", "args": {...}}
    C) Formato legacy: nombre_herramienta({args})
    """
    tool_calls = []
    tool_map = {t.name: t for t in available_tools}

    # ESTRATEGIA A: Patrones explícitos
    explicit_patterns = [
        r"LLAMADA_A_HERRAMIENTA:\s*(\w+)",
        r"Herramienta:\s*(\w+)",
        r"\[TOOL_CALL\]\s*(\w+)",
        r"Tool:\s*(\w+)",
        r"<tool>\s*(\w+)\s*</tool>",
    ]

    for pattern in explicit_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            tool_name = match.group(1)
            if tool_name in tool_map:
                # Buscar JSON de argumentos después del nombre usando extracción balanceada
                remaining_text = text[match.end() :]
                first_curly = remaining_text.find("{")
                args = {}
                if first_curly != -1:
                    json_str = _extract_balanced_json(remaining_text, first_curly)
                    if json_str:
                        try:
                            args = json.loads(json_str)
                        except Exception:
                            pass

                tool_calls.append(
                    {"id": str(uuid.uuid4()), "name": tool_name.strip(), "args": args}
                )

    # ESTRATEGIA B: Bloques JSON estructurados (más fiable)
    # OPTIMIZACIÓN: Limitar escaneo para reducir latencia en respuestas largas
    scan_limit = min(len(text), 5000)
    for i in range(scan_limit):
        if text[i] == "{":
            json_str = _extract_balanced_json(text, i)
            if not json_str:
                continue

            try:
                data = json.loads(json_str)

                # Formato 1: {"name": "...", "args": {...}}
                name = data.get("name") or data.get("tool") or data.get("function")
                args = (
                    data.get("args")
                    or data.get("arguments")
                    or data.get("parameters")
                    or {}
                )

                # Manejar el formato de OpenAI: {"function": {"name": "...", "arguments": "{...}"}}
                if isinstance(name, dict):
                    args_val = name.get("arguments") or name.get("args") or args
                    if isinstance(args_val, str):
                        try:
                            args_val = json.loads(args_val)
                        except Exception:
                            args_val = {}
                    args = args_val
                    name = name.get("name")

                if isinstance(name, str) and name in tool_map:
                    tool_calls.append(
                        {
                            "id": str(uuid.uuid4()),
                            "name": name,
                            "args": args if isinstance(args, dict) else {},
                        }
                    )
                    continue

                # Formato 2: {"tool_name": {...args...}}
                if len(data) == 1:
                    potential_name = list(data.keys())[0]
                    if potential_name in tool_map:
                        potential_args = data[potential_name]
                        tool_calls.append(
                            {
                                "id": str(uuid.uuid4()),
                                "name": potential_name,
                                "args": potential_args
                                if isinstance(potential_args, dict)
                                else {},
                            }
                        )
            except json.JSONDecodeError:
                continue

    # ESTRATEGIA C: Formato legacy tipo código: nombre_herramienta({args})
    legacy_pattern = r"(\w+)\s*\((\{.*?\})\)"
    matches = re.finditer(legacy_pattern, text, re.DOTALL)
    for match in matches:
        potential_name = match.group(1)
        if potential_name in tool_map:
            try:
                args = json.loads(match.group(2))
                tool_calls.append(
                    {
                        "id": str(uuid.uuid4()),
                        "name": potential_name,
                        "args": args if isinstance(args, dict) else {},
                    }
                )
            except Exception:
                continue

    # Eliminar duplicados (mismo nombre y args)
    seen = set()
    unique_calls = []
    for tc in tool_calls:
        key = (tc["name"], json.dumps(tc["args"], sort_keys=True))
        if key not in seen:
            seen.add(key)
            unique_calls.append(tc)

    return unique_calls
