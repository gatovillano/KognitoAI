#!/usr/bin/env python3
"""
KAI Measurement Pipeline - Simplified Version
"""
import json
import sys
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "-q"])
    import requests

API_URL = "http://localhost:8889"

QUERIES = [
    {"id": "query_001", "text": "¿Cuál es la capital de Francia?", "expected": "París", "category": "factual"},
    {"id": "query_002", "text": "¿Qué significa alucinación en IA?", "expected": "Falsificación", "category": "conceptual"},
    {"id": "query_003", "text": "¿Cuánto es 2 más 2?", "expected": "4", "category": "matemática"}
]

def run_measurement_pipeline():
    """Execute measurement pipeline"""
    print("🚀 KAI Measurement Pipeline")
    print("=" * 40)
    
    # Check API health
    print("\n🔍 Checking API health...")
    try:
        resp = requests.get(f"{API_URL}/", timeout=5)
        print(f"   API Status: ✅ Online (HTTP {resp.status_code})")
        api_online = True
    except Exception as e:
        print(f"   API Status: ❌ Offline ({e})")
        api_online = False
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "api_online": api_online,
        "measurements": [],
        "summary": {}
    }
    
    if not api_online:
        return results
    
    print(f"\n📊 Running {len(QUERIES)} measurements...")
    
    for q in QUERIES:
        try:
            # Try different endpoints
            resp = requests.post(
                f"{API_URL}/api/semantic-query",
                json={"query": q["text"]},
                timeout=10
            )
            result = {
                "query_id": q["id"],
                "category": q["category"],
                "response": resp.json(),
                "success": True
            }
            print(f"   ✅ {q['id']}: {q['category']}")
        except Exception as e:
            result = {
                "query_id": q["id"],
                "category": q["category"],
                "error": str(e),
                "success": False
            }
            print(f"   ❌ {q['id']}: {q['category']} (error)")
        
        results["measurements"].append(result)
    
    # Generate summary
    total = len(results["measurements"])
    success = sum(1 for m in results["measurements"] if m.get("success"))
    results["summary"] = {
        "total_queries": total,
        "successful": success,
        "failed": total - success,
        "success_rate": f"{(success/total)*100:.1f}%" if total > 0 else "0%"
    }
    
    print(f"\n📈 Results: {success}/{total} successful ({results['summary']['success_rate']})")
    
    return results

if __name__ == "__main__":
    results = run_measurement_pipeline()
    print("\n" + json.dumps(results, indent=2))
