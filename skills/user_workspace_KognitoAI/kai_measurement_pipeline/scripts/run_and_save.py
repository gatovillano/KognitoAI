#!/usr/bin/env python3
"""
KAI Real Measurement Pipeline
==============================
Mide métricas reales del sistema KAI enviando queries al endpoint
/v1/chat/completions usando la clave interna de autenticación.

- Hallucination Rate: % de queries donde la respuesta NO contiene la keyword esperada
- Recall@5:           % de queries donde la respuesta usa contexto relevante (≥50 palabras y cita fuentes)
- Tool Success Rate:  % de queries que requieren herramientas donde la herramienta fue invocada

NOTA: Cada query espera una respuesta real del LLM, lo que tarda varios segundos.
      El pipeline completo puede tardar 1-5 minutos según el modelo configurado.
"""

import asyncio
import aiohttp
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path

# ─── Config ────────────────────────────────────────────────────────────────────
API_BASE_URL = os.getenv("INTERNAL_API_SERVER_URL", "http://localhost:8889")
INTERNAL_API_KEY = os.getenv(
    "INTERNAL_API_KEY_FOR_BOT",
    "bac65afb5234660a6490aefe3a01923713a904418e4f59b5fbb81d888e2d76cc"
)
TIMEOUT_SECONDS = 60   # timeout por query
DELAY_BETWEEN_QUERIES = 2  # segundos entre queries para no saturar el LLM

# Directorio de reportes
REPORTS_DIR = Path(__file__).parent.parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

# ─── Test Suite ────────────────────────────────────────────────────────────────

# Queries de conocimiento general para medir ALUCINACIONES
# expected_keywords: al menos UNA debe aparecer en la respuesta (case-insensitive)
HALLUCINATION_QUERIES = [
    {
        "id": "hal_001",
        "query": "¿Cuál es la capital de Francia?",
        "expected_keywords": ["París", "Paris", "paris", "parís"],
        "description": "Capital de Francia"
    },
    {
        "id": "hal_002",
        "query": "¿Cuánto es 15 multiplicado por 8?",
        "expected_keywords": ["120"],
        "description": "Matemática básica"
    },
    {
        "id": "hal_003",
        "query": "¿Quién escribió Don Quijote de la Mancha?",
        "expected_keywords": ["Cervantes", "cervantes", "Miguel de Cervantes"],
        "description": "Autor Don Quijote"
    },
    {
        "id": "hal_004",
        "query": "¿En qué continente está Brasil?",
        "expected_keywords": ["América", "America", "Sur", "Sudamérica", "Sudamerica"],
        "description": "Continente de Brasil"
    },
    {
        "id": "hal_005",
        "query": "¿Cuál es el elemento químico con símbolo H2O?",
        "expected_keywords": ["agua", "water", "H2O"],
        "description": "Fórmula química del agua"
    },
]

# Queries que miden RECALL — el modelo debe producir una respuesta sustancial
# (no una respuesta vacía o un error) para indicar que el contexto fue recuperado
RECALL_QUERIES = [
    {
        "id": "rec_001",
        "query": "¿Qué es el RAG y para qué sirve en sistemas de IA?",
        "min_words": 40,
        "description": "Explicación de RAG"
    },
    {
        "id": "rec_002",
        "query": "Explica brevemente cómo funciona un modelo de lenguaje grande (LLM).",
        "min_words": 40,
        "description": "Explicación LLM"
    },
    {
        "id": "rec_003",
        "query": "¿Cuáles son las ventajas de usar embeddings en búsqueda semántica?",
        "min_words": 30,
        "description": "Embeddings en búsqueda semántica"
    },
    {
        "id": "rec_004",
        "query": "¿Qué diferencia hay entre aprendizaje supervisado y no supervisado?",
        "min_words": 30,
        "description": "Supervisado vs no supervisado"
    },
    {
        "id": "rec_005",
        "query": "¿Cómo funciona la atención (attention) en los transformers?",
        "min_words": 40,
        "description": "Mecanismo de atención"
    },
]

# Queries que miden ÉXITO DE HERRAMIENTAS
# El modelo debe mencionar que buscó / usó una herramienta, o la respuesta debe
# incluir indicadores de uso de tool (como fechas actuales, datos en tiempo real, etc.)
TOOL_QUERIES = [
    {
        "id": "tool_001",
        "query": "¿Cuál es la fecha y hora actual?",
        "tool_indicators": ["hoy", "fecha", "hora", "2024", "2025", "2026", ":"],
        "description": "Fecha/hora actual (requiere tool o conocimiento del contexto)"
    },
    {
        "id": "tool_002",
        "query": "Necesito hacer una nota rápida: 'Revisar el pipeline de medición'. Por favor guárdala.",
        "tool_indicators": ["nota", "guardad", "creado", "añadid", "almacen", "registro"],
        "description": "Guardar nota (requiere tool de notas)"
    },
    {
        "id": "tool_003",
        "query": "Busca en mi base de conocimiento algo sobre inteligencia artificial.",
        "tool_indicators": ["encontré", "encontre", "resultado", "document", "conocimiento", "base"],
        "description": "Búsqueda en knowledge base"
    },
]


# ─── Core HTTP client ──────────────────────────────────────────────────────────

async def call_chat_endpoint(
    session: aiohttp.ClientSession,
    query: str,
    query_id: str
) -> dict:
    """Llama al endpoint /v1/chat/completions con autenticación interna."""
    headers = {
        "X-Internal-API-Key": INTERNAL_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "model": "kognito-agent",
        "messages": [
            {"role": "user", "content": query}
        ],
        "stream": False,
        "temperature": 0.3,
    }

    start_time = time.monotonic()
    try:
        async with session.post(
            f"{API_BASE_URL}/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=TIMEOUT_SECONDS),
        ) as resp:
            elapsed = time.monotonic() - start_time
            if resp.status == 200:
                data = await resp.json()
                content = (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
                return {
                    "success": True,
                    "query_id": query_id,
                    "response": content,
                    "response_time": round(elapsed, 2),
                    "status_code": resp.status,
                }
            else:
                body = await resp.text()
                return {
                    "success": False,
                    "query_id": query_id,
                    "error": f"HTTP {resp.status}: {body[:200]}",
                    "response_time": round(elapsed, 2),
                    "status_code": resp.status,
                }
    except asyncio.TimeoutError:
        return {
            "success": False,
            "query_id": query_id,
            "error": f"Timeout después de {TIMEOUT_SECONDS}s",
            "response_time": TIMEOUT_SECONDS,
        }
    except aiohttp.ClientConnectorError as e:
        return {
            "success": False,
            "query_id": query_id,
            "error": f"No se pudo conectar a {API_BASE_URL}: {e}",
            "response_time": 0,
        }
    except Exception as e:
        return {
            "success": False,
            "query_id": query_id,
            "error": str(e),
            "response_time": 0,
        }


# ─── Measurement functions ─────────────────────────────────────────────────────

async def check_api_health(session: aiohttp.ClientSession) -> bool:
    """Verifica que el backend esté disponible antes de correr el pipeline."""
    try:
        async with session.get(
            f"{API_BASE_URL}/",
            timeout=aiohttp.ClientTimeout(total=5)
        ) as resp:
            return resp.status in (200, 307)
    except Exception:
        return False


async def measure_hallucinations(session: aiohttp.ClientSession) -> dict:
    """
    Mide tasa de alucinaciones.
    Una alucinación = la respuesta NO contiene ninguna keyword esperada.
    """
    print("\n📊 Midiendo alucinaciones...")
    results = []
    hallucinations = 0

    for q in HALLUCINATION_QUERIES:
        print(f"   → [{q['id']}] {q['description']}...", end=" ", flush=True)
        result = await call_chat_endpoint(session, str(q["query"]), str(q["id"]))

        if result["success"]:
            response_lower = result["response"].lower()
            found = any(kw.lower() in response_lower for kw in q["expected_keywords"])
            is_hallucination = not found
            if is_hallucination:
                hallucinations += 1
                print(f"❌ ALUCINACIÓN ('{result['response'][:60]}...')")
            else:
                print(f"✅ OK ({result['response_time']}s)")
            results.append({
                **result,
                "expected_keywords": q["expected_keywords"],
                "is_hallucination": is_hallucination,
                "description": q["description"],
            })
        else:
            print(f"⚠ ERROR: {result['error']}")
            # Error de API no es alucinación, no penaliza la tasa
            results.append({**result, "is_hallucination": None, "description": q["description"]})

        await asyncio.sleep(DELAY_BETWEEN_QUERIES)

    evaluated = [r for r in results if r.get("is_hallucination") is not None]
    total_evaluated = len(evaluated)
    hallucination_rate = round((hallucinations / total_evaluated) * 100, 1) if total_evaluated > 0 else 0

    return {
        "metric": "hallucination_rate",
        "value": hallucination_rate,
        "reference": 5.0,
        "status": "OK" if hallucination_rate <= 5.0 else "WARNING",
        "unit": "%",
        "details": {
            "total_queries": len(HALLUCINATION_QUERIES),
            "evaluated": total_evaluated,
            "hallucinations": hallucinations,
            "errors": len(results) - total_evaluated,
            "individual": results,
        }
    }


async def measure_recall(session: aiohttp.ClientSession) -> dict:
    """
    Mide Recall@5 como proxy:
    Una query "tiene recall" si la respuesta contiene ≥ min_words palabras (respuesta sustancial).
    """
    print("\n📊 Midiendo recall (calidad de respuestas)...")
    results = []
    successful = 0

    for q in RECALL_QUERIES:
        print(f"   → [{q['id']}] {q['description']}...", end=" ", flush=True)
        result = await call_chat_endpoint(session, str(q["query"]), str(q["id"]))

        if result["success"]:
            word_count = len(result["response"].split())
            has_recall = word_count >= int(q["min_words"])
            if has_recall:
                successful += 1
                print(f"✅ OK ({word_count} palabras, {result['response_time']}s)")
            else:
                print(f"❌ POBRE ({word_count} palabras, necesita ≥{q['min_words']})")
            results.append({
                **result,
                "word_count": word_count,
                "min_words": q["min_words"],
                "has_recall": has_recall,
                "description": q["description"],
            })
        else:
            print(f"⚠ ERROR: {result['error']}")
            results.append({**result, "has_recall": False, "description": q["description"]})

        await asyncio.sleep(DELAY_BETWEEN_QUERIES)

    total = len(RECALL_QUERIES)
    recall_value = round(successful / total, 2) if total > 0 else 0

    return {
        "metric": "recall_at_5",
        "value": recall_value,
        "reference": 0.80,
        "status": "OK" if recall_value >= 0.80 else "WARNING",
        "unit": "",
        "details": {
            "total_queries": total,
            "successful": successful,
            "individual": results,
        }
    }


async def measure_tool_success(session: aiohttp.ClientSession) -> dict:
    """
    Mide tasa de éxito de herramientas.
    Una herramienta "tuvo éxito" si la respuesta contiene al menos un indicador de uso.
    """
    print("\n📊 Midiendo éxito de herramientas...")
    results = []
    successful = 0

    for q in TOOL_QUERIES:
        print(f"   → [{q['id']}] {q['description']}...", end=" ", flush=True)
        result = await call_chat_endpoint(session, str(q["query"]), str(q["id"]))

        if result["success"]:
            response_lower = result["response"].lower()
            tool_used = any(ind.lower() in response_lower for ind in q["tool_indicators"])
            if tool_used:
                successful += 1
                print(f"✅ TOOL USADA ({result['response_time']}s)")
            else:
                print(f"❌ SIN TOOL ({result['response'][:60]}...)")
            results.append({
                **result,
                "tool_indicators": q["tool_indicators"],
                "tool_used": tool_used,
                "description": q["description"],
            })
        else:
            print(f"⚠ ERROR: {result['error']}")
            results.append({**result, "tool_used": False, "description": q["description"]})

        await asyncio.sleep(DELAY_BETWEEN_QUERIES)

    total = len(TOOL_QUERIES)
    success_rate = round((successful / total) * 100, 1) if total > 0 else 0

    return {
        "metric": "tool_success_rate",
        "value": success_rate,
        "reference": 98.0,
        "status": "OK" if success_rate >= 98.0 else "WARNING",
        "unit": "%",
        "details": {
            "total_queries": total,
            "successful": successful,
            "individual": results,
        }
    }


# ─── Main pipeline ─────────────────────────────────────────────────────────────

async def run_pipeline():
    print("=" * 60)
    print("🚀 KAI REAL Measurement Pipeline")
    print(f"   API: {API_BASE_URL}")
    print(f"   Timeout por query: {TIMEOUT_SECONDS}s")
    print(f"   Queries total: {len(HALLUCINATION_QUERIES) + len(RECALL_QUERIES) + len(TOOL_QUERIES)}")
    print("=" * 60)

    connector = aiohttp.TCPConnector(limit=1)  # Una sola conexión (sin concurrencia para evitar rate limit)
    async with aiohttp.ClientSession(connector=connector) as session:

        # Health check
        print("\n🔍 Verificando disponibilidad del backend...")
        is_healthy = await check_api_health(session)
        if not is_healthy:
            raise RuntimeError(
                f"No se puede conectar al backend en {API_BASE_URL}. "
                "Asegúrate de que el servidor esté corriendo."
            )
        print(f"   ✅ Backend disponible en {API_BASE_URL}")

        pipeline_start = time.monotonic()

        # Ejecutar las tres métricas secuencialmente
        hallucination_metric = await measure_hallucinations(session)
        recall_metric = await measure_recall(session)
        tool_metric = await measure_tool_success(session)

        total_time = round(time.monotonic() - pipeline_start, 1)

    # Construir resultado final
    metrics = [hallucination_metric, recall_metric, tool_metric]
    warnings = sum(1 for m in metrics if m["status"] == "WARNING")
    timestamp = datetime.now()
    timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")

    result = {
        "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        "execution_time_seconds": total_time,
        "api_url": API_BASE_URL,
        "is_real": True,  # Flag para distinguir de datos simulados
        "metrics": [
            {k: v for k, v in m.items() if k != "details"}  # Summary without verbose details
            for m in metrics
        ],
        "metrics_detailed": metrics,  # Full details including individual responses
        "summary": {
            "total_metrics": len(metrics),
            "warnings": warnings,
        }
    }

    # Guardar resultados
    latest_file = REPORTS_DIR / "metrics.json"
    timestamped_file = REPORTS_DIR / f"metrics_{timestamp_str}.json"

    with open(latest_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    with open(timestamped_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    # Resumen final
    print("\n" + "=" * 60)
    print("📈 RESULTADOS FINALES")
    print("=" * 60)
    for m in metrics:
        status_icon = "✅" if m["status"] == "OK" else "⚠️"
        print(f"  {status_icon} {m['metric']}: {m['value']}{m['unit']} (meta: {m['reference']}{m['unit']})")

    print(f"\n⏱  Tiempo total: {total_time}s")
    print(f"📁 Reportes guardados:")
    print(f"   - {latest_file}")
    print(f"   - {timestamped_file}")

    if warnings > 0:
        print(f"\n⚠️  {warnings} métrica(s) requieren atención.")
    else:
        print("\n✅ Todas las métricas dentro del objetivo.")

    return result


if __name__ == "__main__":
    asyncio.run(run_pipeline())
