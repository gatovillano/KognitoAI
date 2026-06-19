import json
from pathlib import Path

RESULTS_PATH = Path(__file__).parent.parent / "results" / "raw_responses.json"
METRICS_PATH = Path(__file__).parent.parent / "results" / "metrics_summary.csv"

# Simulación de función para detectar alucinaciones (debería ser reemplazada por lógica real)
def is_hallucination(response, expected_answer):
    if expected_answer is None:
        return False
    return response.strip().lower() != expected_answer.strip().lower()

def main():
    with open(RESULTS_PATH) as f:
        results = json.load(f)
    total = len(results)
    hallucinations = 0
    tool_success = 0
    total_tools = 0
    latencies = []
    for r in results:
        if is_hallucination(r["response"], r["expected_answer"]):
            hallucinations += 1
        if r["expected_tool"]:
            total_tools += 1
            if r["tool_used"] == r["expected_tool"]:
                tool_success += 1
        latencies.append(r["latency"])
    hallucination_rate = hallucinations / total if total else 0
    tool_success_rate = tool_success / total_tools if total_tools else 0
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    with open(METRICS_PATH, "w") as f:
        f.write("metric,value\n")
        f.write(f"hallucination_rate,{hallucination_rate:.2f}\n")
        f.write(f"tool_success_rate,{tool_success_rate:.2f}\n")
        f.write(f"avg_latency,{avg_latency:.2f}\n")
    print(f"Guardado en {METRICS_PATH}")

if __name__ == "__main__":
    main()
