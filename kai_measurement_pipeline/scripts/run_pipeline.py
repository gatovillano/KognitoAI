import csv
import json
import time
from pathlib import Path
import requests

DATASET_PATH = Path(__file__).parent.parent / "datasets" / "prompts_base.csv"
RESULTS_PATH = Path(__file__).parent.parent / "results" / "raw_responses.json"
API_URL = "http://localhost:8000/v1/chat/completions"  # Cambia esto si tu API corre en otro puerto o dominio
API_TOKEN = None  # Si necesitas autenticación, pon el token aquí
MODEL = "gemini/gemini-2.0-flash"  # Ajusta según tu despliegue

def query_kognito_ai(prompt, expected_tool=None):
    headers = {"Content-Type": "application/json"}
    if API_TOKEN:
        headers["Authorization"] = f"Bearer {API_TOKEN}"
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    start = time.time()
    try:
        resp = requests.post(API_URL, headers=headers, json=payload, timeout=60)
        latency = time.time() - start
        if resp.status_code == 200:
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return {
                "response": content,
                "tool_used": None,  # Puedes parsear si tu modelo responde con tool_call
                "latency": latency,
                "success": True
            }
        else:
            return {"response": f"Error {resp.status_code}: {resp.text}", "tool_used": None, "latency": latency, "success": False}
    except Exception as e:
        return {"response": str(e), "tool_used": None, "latency": 0, "success": False}

def main():
    results = []
    with open(DATASET_PATH, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            prompt = row["prompt"]
            expected_tool = row["expected_tool"] or None
            result = query_kognito_ai(prompt, expected_tool)
            result["prompt"] = prompt
            result["expected_tool"] = expected_tool
            result["expected_answer"] = row["expected_answer"]
            result["category"] = row["category"]
            results.append(result)
    with open(RESULTS_PATH, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Guardado en {RESULTS_PATH}")

if __name__ == "__main__":
    main()
