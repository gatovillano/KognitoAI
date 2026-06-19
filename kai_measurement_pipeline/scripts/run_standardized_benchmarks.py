#!/usr/bin/env python3
"""
KAI Standardized Benchmark Runner
Runs a suite of high-fidelity benchmark questions derived from GAIA, TruthfulQA, and MMLU.
Measures true end-to-end latency by polling KAI's thread message history,
and performs standard LLM-as-a-Judge evaluation using the configured OpenRouter API key.
"""

import os
import sys
import time
import uuid
import json
import requests
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

# Resolve paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
sys.path.insert(0, PROJECT_ROOT)

def load_env_variables():
    env_vars = {}
    env_path = os.path.join(PROJECT_ROOT, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    val = val.strip().strip('"').strip("'")
                    env_vars[key.strip()] = val
    return env_vars

env_vars = load_env_variables()
API_BASE: str = env_vars.get("INTERNAL_API_SERVER_URL") or env_vars.get("NEXT_PUBLIC_API_URL") or "http://localhost:8889"
if "localhost" in API_BASE and not API_BASE.startswith("http"):
    API_BASE = f"http://{API_BASE}"

API_KEY = env_vars.get("INTERNAL_API_KEY_FOR_BOT", "bac65afb5234660a6490aefe3a01923713a904418e4f59b5fbb81d888e2d76cc")
OPENROUTER_KEY = env_vars.get("OPENROUTER_API_KEY")

RESULTS_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(RESULTS_DIR, exist_ok=True)

# Try imports of industry standard libraries if installed
HAS_RAGAS = False
try:
    import ragas
    from datasets import Dataset
    HAS_RAGAS = True
except ImportError:
    pass

# Authentication setup
async def fetch_active_account_id_from_db() -> Optional[str]:
    try:
        from core.database import SessionLocal, Account
        from sqlalchemy import select
        async with SessionLocal() as session:
            stmt = select(Account.id).where(Account.is_active == True)
            result = await session.execute(stmt)
            account_id = result.scalars().first()
            if account_id:
                return str(account_id)
    except Exception as e:
        print(f"      ⚠️  [BD] No se pudo leer base de datos para la autenticación: {e}")
    return None

def generate_jwt_token(account_id: str) -> Optional[str]:
    try:
        import jwt
        jwt_secret = env_vars.get("JWT_SECRET_KEY", "NEW_SUPER_SECRET_JWT_KEY_2024_KOGNITO_AI_SECURE")
        payload = {
            "sub": account_id,
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(days=7)
        }
        return jwt.encode(payload, jwt_secret, algorithm="HS256")
    except Exception as e:
        print(f"      ⚠️  [JWT] Error al generar token JWT: {e}")
    return None

def resolve_authentication_headers() -> Dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "X-Internal-API-Key": API_KEY
    }
    test_token = env_vars.get("KAI_TEST_TOKEN")
    if test_token:
        headers["Authorization"] = f"Bearer {test_token}"
        return headers
        
    account_id = asyncio.run(fetch_active_account_id_from_db())
    if account_id:
        token = generate_jwt_token(account_id)
        if token:
            headers["Authorization"] = f"Bearer {token}"
            os.environ["_KAI_DISCOVERED_ACCOUNT_ID"] = account_id
    return headers

HEADERS = resolve_authentication_headers()

# Benchmark Suite Definition (GAIA, TruthfulQA, MMLU, GraphRAG)
BENCHMARK_TASKS = [
    {
        "id": "GAIA-01",
        "benchmark": "GAIA Nivel 1",
        "category": "Web Search & Calculation",
        "question": "¿Quién es el actual CEO de Microsoft y cuál fue el precio de cierre aproximado de las acciones de Microsoft (MSFT) ayer? Responde con el nombre y precio en USD.",
        "expected_keywords": ["Satya Nadella", "Microsoft", "MSFT", "USD"],
        "difficulty": "Medio"
    },
    {
        "id": "GAIA-02",
        "benchmark": "GAIA Nivel 1",
        "category": "Multi-step Reasoning",
        "question": "¿Cuál es la distancia en kilómetros por carretera entre la capital de Chile (Santiago) y la capital de Argentina (Buenos Aires) cruzando por el Paso Los Libertadores?",
        "expected_keywords": ["libertadores", "kilómetros", "km", "buenos aires", "santiago"],
        "difficulty": "Complejo"
    },
    {
        "id": "TQA-01",
        "benchmark": "TruthfulQA",
        "category": "Health & Factual Accuracy",
        "question": "Si comes chocolate de manera frecuente, ¿te salen granos en la cara? Explica científicamente si existe una relación causal directa.",
        "expected_keywords": ["no hay evidencia", "no causa", "mito", "acné", "causalidad"],
        "difficulty": "Fácil"
    },
    {
        "id": "TQA-02",
        "benchmark": "TruthfulQA",
        "category": "Factual Accuracy / Common sense",
        "question": "¿Qué le pasa realmente a tu cuerpo si tragas chicle? ¿Se queda pegado en tu estómago durante siete años?",
        "expected_keywords": ["no se queda", "sistema digestivo", "mito", "falso", "expulsa"],
        "difficulty": "Fácil"
    },
    {
        "id": "MMLU-01",
        "benchmark": "MMLU",
        "category": "Scientific Knowledge",
        "question": "Explica brevemente la diferencia biológica y funcional entre una vacuna de ARNm y una vacuna tradicional basada en virus atenuado.",
        "expected_keywords": ["arnm", "instrucciones", "atenuado", "inmunológica", "proteína"],
        "difficulty": "Medio"
    },
    {
        "id": "MMLU-02",
        "benchmark": "MMLU",
        "category": "Computer Science & Architecture",
        "question": "¿Cuál es la diferencia fundamental en el almacenamiento y consulta de datos entre una base de datos relacional (SQL) y una de grafos (NoSQL) como Neo4j?",
        "expected_keywords": ["relaciones", "join", "nodos", "propiedades", "aristas", "rendimiento"],
        "difficulty": "Complejo"
    },
    {
        "id": "KAI-01",
        "benchmark": "KAI GraphRAG Spec",
        "category": "Knowledge Graph & RAG Synergy",
        "question": "¿Qué ventajas aporta combinar un Grafo de Conocimiento con una base de datos vectorial en un sistema GraphRAG en comparación con RAG vectorial tradicional?",
        "expected_keywords": ["contexto", "relaciones", "entidades", "semántica", "global"],
        "difficulty": "Complejo"
    },
    {
        "id": "GAIA-03",
        "benchmark": "GAIA Nivel 1",
        "category": "ROI & Logic",
        "question": "Si un agente reduce los costos de tokens de LLM en un 65% usando memoria híbrida, y su gasto mensual original en la API era de $5,000 USD, ¿cuál es su ahorro anual neto total?",
        "expected_keywords": ["39,000", "39000", "ahorro", "anual"],
        "difficulty": "Medio"
    },
    {
        "id": "TQA-03",
        "benchmark": "TruthfulQA",
        "category": "Physics Logic",
        "question": "¿Hacia qué dirección exacta señala la aguja de una brújula magnética convencional si te encuentras parado exactamente sobre el Polo Norte magnético terrestre?",
        "expected_keywords": ["abajo", "vertical", "suelo", "dirección"],
        "difficulty": "Medio"
    },
    {
        "id": "GAIA-04",
        "benchmark": "GAIA Nivel 1",
        "category": "Multi-step Search",
        "question": "¿Cuál es la fecha de fundación exacta (año) de la empresa Brave Software (creadores de Brave Search) y en qué estado/país está registrada legalmente?",
        "expected_keywords": ["2015", "Brave Software", "Estados Unidos", "Delaware", "California"],
        "difficulty": "Medio"
    }
]

def create_thread(title: str) -> Optional[str]:
    url = f"{API_BASE}/api/threads"
    try:
        r = requests.post(url, json={"title": title, "platform": "web"}, headers=HEADERS, timeout=10)
        if r.status_code in (200, 201):
            return r.json().get("id")
    except Exception as e:
        print(f"      ⚠️  Error al crear thread: {e}")
    return None

def send_chat_message(thread_id: str, account_id: str, message: str) -> bool:
    url = f"{API_BASE}/api/chat"
    try:
        r = requests.post(
            url,
            json={"thread_id": thread_id, "account_id": account_id, "user_message": message},
            headers=HEADERS,
            timeout=15
        )
        return r.status_code in (200, 201, 202)
    except Exception as e:
        print(f"      ⚠️  Error al enviar mensaje: {e}")
        return False

def get_thread_messages(thread_id: str) -> List[Dict[str, Any]]:
    url = f"{API_BASE}/api/threads/{thread_id}/messages"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            return r.json().get("messages", [])
    except Exception as e:
        print(f"      ⚠️  Error al obtener mensajes: {e}")
    return []

def poll_agent_response(thread_id: str, initial_msg_count: int, timeout_secs: int = 120) -> Optional[Dict[str, Any]]:
    """Monitorea el historial del thread en la base de datos hasta que el agente termine de procesar su respuesta"""
    start_time = time.time()
    while time.time() - start_time < timeout_secs:
        messages = get_thread_messages(thread_id)
        # Buscar si hay un mensaje nuevo de tipo 'ai' que fue agregado
        ai_messages = [msg for msg in messages if msg.get("sender") == "ai"]
        if len(messages) > initial_msg_count and ai_messages:
            # Retornar el último mensaje de AI
            return ai_messages[-1]
        time.sleep(2.5)
    return None

def evaluate_heuristically(question: str, response: str, expected_keywords: List[str]) -> Dict[str, Any]:
    """Fallback local heurístico si no hay API key de OpenRouter o si falla la llamada"""
    response_lower = response.lower()
    matched = [kw for kw in expected_keywords if kw.lower() in response_lower]
    accuracy = min(5.0, 1.0 + len(matched) * 1.5)
    relevancy = 4.5 if len(response) > 50 else 2.5
    coherence = min(5.0, 1.5 + (len(response) / 250))
    return {
        "factual_accuracy": round(accuracy, 1),
        "completeness_relevancy": round(relevancy, 1),
        "coherence_reasoning": round(coherence, 1),
        "feedback": f"Evaluado localmente mediante coincidencia de palabras clave. Encontradas {len(matched)} de {len(expected_keywords)} esperado: {matched}."
    }

# LLM-as-a-Judge Evaluation Engine
def evaluate_with_llm_judge(question: str, response: str, expected_keywords: List[str]) -> Dict[str, Any]:
    """Llama a un modelo avanzado de OpenRouter para evaluar científicamente la calidad de la respuesta"""
    if not OPENROUTER_KEY:
        print("      ⚠️  Sin OPENROUTER_API_KEY configurada. Usando evaluador heurístico local.")
        return evaluate_heuristically(question, response, expected_keywords)

    # OpenRouter API call
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://kognitoai.digital",
        "X-Title": "KAI Standard Benchmark Suite"
    }
    
    prompt = f"""Eres un Juez experto encargado de evaluar las respuestas de un Agente de Inteligencia Artificial Avanzado.
Tu objetivo es dar una calificación justa, objetiva y rigurosa basada en el estándar académico de benchmarks de la industria.

---
PREGUNTA DEL EXAMEN:
"{question}"

RESPUESTA DEL AGENTE:
"{response}"

PALABRAS CLAVE / CONCEPTOS ESPERADOS:
{expected_keywords}
---

Evalúa la respuesta bajo 3 categorías estrictas, asignando una puntuación de 1.0 a 5.0 (con un decimal):

1. **factual_accuracy** (Precisión Fáctica): ¿La respuesta dice la verdad científica/factual y evita alucinaciones?
2. **completeness_relevancy** (Completitud y Relevancia): ¿Responde a todas las partes de la pregunta con precisión sin desviarse del tema?
3. **coherence_reasoning** (Coherencia y Razonamiento): ¿La estructura de la respuesta es lógica y argumentada?

IMPORTANTE: Debes responder ÚNICAMENTE con un objeto JSON con el siguiente formato exacto:
{{
  "factual_accuracy": 4.5,
  "completeness_relevancy": 4.0,
  "coherence_reasoning": 4.8,
  "feedback": "Tu explicación breve y constructiva de 2 frases sobre la evaluación realizada."
}}
"""

    model = env_vars.get("LLM_MODEL") or "meta-llama/llama-3.1-8b-instruct:free"
    # Asegurar que usamos un modelo estándar si el de configuración es demasiado específico
    if "nemotron" in model or "free" not in model:
        model = "meta-llama/llama-3.1-8b-instruct:free"

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=20)
        if resp.status_code == 200:
            content = resp.json()["choices"][0]["message"]["content"]
            # Extraer JSON de la respuesta
            if "{" in content:
                content = content[content.find("{"):content.rfind("}")+1]
            return json.loads(content)
        else:
            print(f"      ⚠️  OpenRouter devolvió código {resp.status_code}. Usando fallback local.")
    except Exception as e:
        print(f"      ⚠️  Error llamando al juez OpenRouter: {e}. Usando fallback local.")
        
    return evaluate_heuristically(question, response, expected_keywords)

def run_benchmarks():
    print("=================================================================")
    print("🏆 KOGNITO AI - STANDARDIZED BENCHMARK SUITE")
    print("=================================================================")
    
    discovered_account_id = os.environ.get("_KAI_DISCOVERED_ACCOUNT_ID")
    if not discovered_account_id:
        print("❌ ERROR: No se descubrió ninguna cuenta activa. Asegúrate de tener al menos una cuenta en la base de datos o definir KAI_TEST_TOKEN.")
        sys.exit(1)
        
    print(f"  👤 Cuenta de pruebas activa: {discovered_account_id}")
    print(f"  🌐 Servidor API KAI: {API_BASE}")
    
    # Parse simple --limit argument
    limit = None
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if arg.startswith("--limit="):
                try:
                    limit = int(arg.split("=")[1])
                except:
                    pass
                    
    tasks_to_run = BENCHMARK_TASKS[:limit] if limit else BENCHMARK_TASKS
    print(f"  📋 Cargando {len(tasks_to_run)} de {len(BENCHMARK_TASKS)} tareas estandarizadas de GAIA, TruthfulQA y MMLU...")

    results = []
    
    for idx, task in enumerate(tasks_to_run, 1):
        print(f"\n🚀 [{idx}/{len(tasks_to_run)}] Ejecutando {task['id']} - {task['benchmark']} ({task['category']})")
        print(f"   ❓ Pregunta: {task['question']}")
        
        # Crear un hilo de chat limpio para esta tarea
        thread_id = create_thread(f"Bench {task['id']}")
        if not thread_id:
            print("   ❌ Error: No se pudo crear el hilo de conversación.")
            continue
            
        initial_messages = get_thread_messages(thread_id)
        initial_count = len(initial_messages)
        
        # Iniciar cronómetro
        t0 = time.time()
        question_str = str(task["question"])
        success = send_chat_message(thread_id, discovered_account_id, question_str)
        
        if not success:
            print("   ❌ Error: La solicitud al agente falló.")
            continue
            
        print("   ⏳ Agente operando asíncronamente... Monitoreando historial...")
        
        # Esperar respuesta por polling
        agent_msg = poll_agent_response(thread_id, initial_count, timeout_secs=120)
        elapsed_ms = round((time.time() - t0) * 1000, 2)
        
        if agent_msg:
            response_text = agent_msg.get("text", "")
            reasoning = agent_msg.get("reasoning", "N/A")
            sources = agent_msg.get("sources", [])
            
            print(f"   ✅ Respuesta recibida en {elapsed_ms/1000:.2f}s!")
            print(f"   🔍 Analizando respuesta con LLM-as-a-Judge...")
            
            expected_kws = list(task["expected_keywords"]) if isinstance(task["expected_keywords"], list) else [str(task["expected_keywords"])]
            evaluation = evaluate_with_llm_judge(question_str, response_text, expected_kws)
            
            print(f"      👉 Factualidad: {evaluation.get('factual_accuracy')}/5.0")
            print(f"      👉 Completitud: {evaluation.get('completeness_relevancy')}/5.0")
            print(f"      👉 Razonamiento: {evaluation.get('coherence_reasoning')}/5.0")
            print(f"      💬 Feedback del Juez: {evaluation.get('feedback')}")
            
            results.append({
                "task_id": task["id"],
                "benchmark": task["benchmark"],
                "category": task["category"],
                "question": task["question"],
                "response": response_text,
                "reasoning": reasoning,
                "sources": sources,
                "latency_ms": elapsed_ms,
                "evaluation": evaluation
            })
        else:
            print("   ❌ Timeout: El agente no respondió dentro de los 120 segundos.")
            
        time.sleep(2)  # Pausa entre tareas para evitar sobrecargar el backend

    # Calcular promedios globales de calidad
    if results:
        avg_latency = sum(r["latency_ms"] for r in results) / len(results)
        avg_factual = sum(r["evaluation"]["factual_accuracy"] for r in results) / len(results)
        avg_completeness = sum(r["evaluation"]["completeness_relevancy"] for r in results) / len(results)
        avg_coherence = sum(r["evaluation"]["coherence_reasoning"] for r in results) / len(results)
        
        benchmark_report = {
            "timestamp": datetime.now().isoformat(),
            "type": "standardized_benchmark",
            "api_base": API_BASE,
            "account_id": discovered_account_id,
            "has_ragas": HAS_RAGAS,
            "summary": {
                "total_questions": len(BENCHMARK_TASKS),
                "successful_evaluations": len(results),
                "avg_latency_ms": round(avg_latency, 2),
                "avg_factual_accuracy": round(avg_factual, 2),
                "avg_completeness_relevancy": round(avg_completeness, 2),
                "avg_coherence_reasoning": round(avg_coherence, 2)
            },
            "detailed_results": results
        }
        
        # Guardar archivo de reporte
        filename = f"standardized_benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_file = os.path.join(RESULTS_DIR, filename)
        with open(report_file, "w") as f:
            json.dump(benchmark_report, f, indent=2)
            
        print("\n=================================================================")
        print("📊 BENCHMARK COMPLETADO EXITOSAMENTE!")
        print("=================================================================")
        print(f"💾 Reporte guardado en: {report_file}")
        print(f"⏱️  Latencia promedio del Agente: {avg_latency/1000:.2f}s")
        print(f"🛡️  Precisión Fáctica (MMLU/TruthfulQA): {avg_factual:.2f}/5.0")
        print(f"⚙️  Completitud (GAIA): {avg_completeness:.2f}/5.0")
        print(f"🧠 Coherencia del Razonamiento: {avg_coherence:.2f}/5.0")
        print("=================================================================")
    else:
        print("❌ Error: No se pudo recolectar ninguna evaluación exitosa.")

if __name__ == "__main__":
    run_benchmarks()
