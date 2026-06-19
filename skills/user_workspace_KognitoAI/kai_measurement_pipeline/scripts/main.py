#!/usr/bin/env python3
"""
KAI Measurement Pipeline - Main Entry Point
"""
import json
import sys
from pathlib import Path
from datetime import datetime

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent))

from local_analyzer import LocalAnalyzer

def run_pipeline():
    """Run the complete measurement pipeline"""
    print("🚀 KAI Measurement Pipeline")
    print("=" * 40)
    
    # Load config
    config_path = Path(__file__).parent.parent / "config.json"
    with open(config_path) as f:
        config = json.load(f)
    
    # Initialize analyzer
    analyzer = LocalAnalyzer()
    
    # Sample responses (simulating KAI responses)
    sample_responses = {
        "query_001": "La capital de Francia es París. París es una ciudad importante en Europa.",
        "query_002": "En el contexto de IA, una alucinación es cuando el modelo genera información falsa o incorrecta que parece creíble.",
        "query_003": "2 más 2 es igual a 4. Esta es una operación matemática básica."
    }
    
    # Process each query
    print(f"\n📊 Processing {len(config['measurement_queries'])} queries...")
    
    results = []
    for query in config['measurement_queries']:
        query_id = query['id']
        query_text = query['text']
        category = query['category']
        
        # Get simulated response
        response = sample_responses.get(query_id, "Respuesta procesada correctamente.")
        
        # Analyze
        result = analyzer.analyze_response(query_text, response, category)
        results.append(result)
        
        status = "✅" if result['is_correct'] else "❌"
        print(f"   {status} {query_id}: {category} ({result['quality_score']:.2f})")
    
    # Get summary
    summary = analyzer.get_summary()
    
    # Save results
    reports_dir = Path(__file__).parent.parent / "reports"
    reports_dir.mkdir(exist_ok=True)
    
    metrics = {
        "timestamp": datetime.now().isoformat(),
        **summary
    }
    
    with open(reports_dir / "metrics.json", 'w') as f:
        json.dump(metrics, f, indent=2)
    
    print(f"\n📈 Summary:")
    print(f"   Total: {summary['total_queries']}")
    print(f"   Exitosas: {summary['successful']}")
    print(f"   Fallidas: {summary['failed']}")
    print(f"   Tasa: {summary['success_rate']}")
    
    print(f"\n✅ Pipeline completed! Reports saved to {reports_dir}")
    return metrics

if __name__ == "__main__":
    run_pipeline()
