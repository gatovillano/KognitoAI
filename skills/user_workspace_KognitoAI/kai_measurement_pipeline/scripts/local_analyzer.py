#!/usr/bin/env python3
"""
KAI Local Analyzer - Analyzes responses without external API
"""
import re
from typing import Dict, Any, List

class LocalAnalyzer:
    def __init__(self):
        self.metrics = {
            "total_queries": 0,
            "successful": 0,
            "failed": 0,
            "categories": {}
        }
    
    def analyze_response(self, query: str, response: str, category: str) -> Dict[str, Any]:
        """Analyze response quality locally"""
        result = {
            "query": query,
            "category": category,
            "response_length": len(response),
            "word_count": len(response.split()),
            "has_confidence": "confianza" in response.lower() or "confidence" in response.lower(),
            "is_correct": self._check_answer(query, response),
            "quality_score": self._calculate_quality(response)
        }
        
        # Update metrics
        self.metrics["total_queries"] += 1
        if result["is_correct"]:
            self.metrics["successful"] += 1
        else:
            self.metrics["failed"] += 1
        
        if category not in self.metrics["categories"]:
            self.metrics["categories"][category] = {"total": 0, "correct": 0}
        self.metrics["categories"][category]["total"] += 1
        if result["is_correct"]:
            self.metrics["categories"][category]["correct"] += 1
        
        return result
    
    def _check_answer(self, query: str, response: str) -> bool:
        """Simple answer checking logic"""
        response_lower = response.lower()
        
        # Check for refusal or error patterns
        refusal_patterns = [
            "no tengo información",
            "no puedo ayudar",
            "error",
            "no disponible",
            "no está claro"
        ]
        
        for pattern in refusal_patterns:
            if pattern in response_lower:
                return False
        
        return len(response.strip()) > 10
    
    def _calculate_quality(self, response: str) -> float:
        """Calculate response quality score (0-1)"""
        if not response.strip():
            return 0.0
        
        score = 0.5  # Base score
        
        # Length bonus
        if len(response) > 50:
            score += 0.2
        if len(response) > 100:
            score += 0.1
        
        # Structure bonus
        if any(p in response for p in [".", "!", "?"]):
            score += 0.1
        
        return min(1.0, score)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary"""
        total = self.metrics["total_queries"]
        if total > 0:
            self.metrics["success_rate"] = f"{(self.metrics['successful']/total)*100:.1f}%"
        return self.metrics

if __name__ == "__main__":
    # Test the analyzer
    analyzer = LocalAnalyzer()
    
    test_queries = [
        ("¿Quién es Einstein?", "Albert Einstein fue un físico teórico alemán.", "factual"),
        ("¿Cuál es 2+2?", "La respuesta es 4.", "matemática"),
        ("¿Dónde está París?", "París está en Francia.", "geografía")
    ]
    
    for query, response, category in test_queries:
        result = analyzer.analyze_response(query, response, category)
        print(f"✅ {query}")
        print(f"   Category: {category}")
        print(f"   Quality: {result['quality_score']:.2f}")
        print()
    
    print("Summary:", analyzer.get_summary())
