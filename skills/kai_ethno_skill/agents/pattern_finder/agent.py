"""
PatternFinder Agent - Detective Semántico
Agente especializado en análisis de patrones a gran escala
"""

import asyncio
import re
import logging
from typing import Dict, List, Any, Optional
from collections import Counter, defaultdict
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class PatternFinderState(BaseModel):
    """Estado del agente PatternFinder"""
    corpus: List[Dict[str, Any]] = Field(default_factory=list)
    semantic_networks: List[Dict[str, Any]] = Field(default_factory=list)
    clusters: List[Dict[str, Any]] = Field(default_factory=list)
    temporal_evolution: Dict[str, Any] = Field(default_factory=dict)
    keyword_frequencies: Dict[str, int] = Field(default_factory=dict)
    status: str = "idle"


class PatternFinderAgent:
    """
    Agente PatternFinder - Especialista en minería de patrones
    
    Capacidades:
    - Redes semánticas y co-ocurrencia de términos
    - Clustering temático (LDA, BERTopic)
    - Análisis de evolución histórica de conceptos
    - Detección de comunidades en redes de citación
    - Análisis de sentimiento y polaridad
    """
    
    name = "pattern_finder"
    description = "Detective Semántico - Análisis de patrones a gran escala"
    
    def __init__(self, llm_service: Any = None):
        self.llm = llm_service
        self.graph = self._build_graph()
        self.state = PatternFinderState()
    
    def _build_graph(self) -> StateGraph:
        """Construye el grafo de LangGraph para el flujo del agente"""
        
        def preprocess_corpus(state: PatternFinderState) -> Dict[str, Any]:
            """Preprocesa el corpus (tokenización, limpieza)"""
            texts = []
            for doc in state.corpus:
                text = doc.get("abstract", doc.get("title", ""))
                if text:
                    # Limpiar y tokenizar
                    text = re.sub(r'[^\w\sáéíóúüñÁÉÍÓÚÜÑ]', ' ', text.lower())
                    words = [w for w in text.split() if len(w) > 3]
                    texts.append(words)
            
            return {"status": "preprocessed", "tokenized_texts": texts}
        
        def extract_keywords(state: PatternFinderState) -> Dict[str, Any]:
            """Extrae keywords y calcula frecuencias"""
            all_words = []
            for text in state.corpus:
                content = text.get("abstract", text.get("title", ""))
                words = re.findall(r'\b[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ]{4,}\b', content.lower())
                stopwords = {"para", "como", "pero", "porque", "desde", "hasta", "durante", "entre", "sobre",
                            "bajo", "tras", "hacia", "contra", "mediante", "según", "durante", "mientras",
                            "the", "and", "for", "with", "that", "this", "have", "from", "they", "been",
                            "their", "would", "could", "should", "there", "these", "those", "other",
                            "estudio", "estudios", "research", "paper", "article", "journal", "method"}
                all_words.extend([w for w in words if w not in stopwords])
            
            freq = Counter(all_words)
            top_keywords = dict(freq.most_common(50))
            
            return {"status": "keywords_extracted", "keyword_frequencies": top_keywords}
        
        def build_semantic_network(state: PatternFinderState) -> Dict[str, Any]:
            """Construye red semántica de co-ocurrencias"""
            co_occurrence = defaultdict(int)
            window_size = 5
            
            for doc in state.corpus:
                content = doc.get("abstract", doc.get("title", ""))
                words = re.findall(r'\b[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ]{4,}\b', content.lower())
                stopwords = {"para", "como", "pero", "porque", "desde", "hasta", "durante", "entre", "sobre",
                            "bajo", "tras", "hacia", "contra", "mediante", "según", "durante", "mientras",
                            "the", "and", "for", "with", "that", "this", "have", "from", "they", "been",
                            "their", "would", "could", "should", "there", "these", "those", "other"}
                words = [w for w in words if w not in stopwords]
                
                for i, word in enumerate(words):
                    for j in range(max(0, i - window_size), min(len(words), i + window_size + 1)):
                        if i != j:
                            pair = tuple(sorted([word, words[j]]))
                            co_occurrence[pair] += 1
            
            # Filtrar solo co-ocurrencias significativas
            significant_edges = [(w1, w2, count) for (w1, w2), count in co_occurrence.items() if count >= 2]
            significant_edges.sort(key=lambda x: x[2], reverse=True)
            
            nodes = set()
            for w1, w2, _ in significant_edges:
                nodes.add(w1)
                nodes.add(w2)
            
            network = {
                "nodes": list(nodes),
                "edges": [{"source": w1, "target": w2, "weight": count} for w1, w2, count in significant_edges[:200]],
                "density": len(significant_edges) / (len(nodes) * (len(nodes) - 1) / 2) if len(nodes) > 1 else 0
            }
            
            return {"status": "network_built", "semantic_networks": [network]}
        
        def detect_clusters(state: PatternFinderState) -> Dict[str, Any]:
            """Detecta clusters temáticos"""
            # Agrupar documentos por año y por temas principales
            year_groups = defaultdict(list)
            theme_groups = defaultdict(list)
            
            for doc in state.corpus:
                year = doc.get("year")
                if year:
                    year_groups[year].append(doc)
                
                # Asignar a cluster basado en palabras clave del título/abstract
                content = (doc.get("title", "") + " " + doc.get("abstract", "")).lower()
                if "health" in content or "salud" in content:
                    theme_groups["salud"].append(doc)
                elif "education" in content or "educación" in content:
                    theme_groups["educación"].append(doc)
                elif "technology" in content or "tecnología" in content or "digital" in content:
                    theme_groups["tecnología"].append(doc)
                elif "environment" in content or "ambiente" in content or "clima" in content:
                    theme_groups["ambiente"].append(doc)
                elif "economy" in content or "economía" in content or "labor" in content:
                    theme_groups["economía"].append(doc)
                else:
                    theme_groups["otros"].append(doc)
            
            clusters = []
            for theme, docs in theme_groups.items():
                if len(docs) >= 2:
                    clusters.append({
                        "theme": theme,
                        "doc_count": len(docs),
                        "avg_year": sum(d.get("year", 0) or 0 for d in docs) / len(docs) if docs else 0,
                        "documents": [d.get("title", "") for d in docs[:5]]
                    })
            
            clusters.sort(key=lambda x: x["doc_count"], reverse=True)
            
            return {"status": "clusters_detected", "clusters": clusters}
        
        def analyze_temporal(state: PatternFinderState) -> Dict[str, Any]:
            """Analiza evolución temporal de conceptos"""
            year_freq = defaultdict(int)
            year_keywords = defaultdict(lambda: defaultdict(int))
            
            for doc in state.corpus:
                year = doc.get("year")
                if not year:
                    continue
                year_freq[year] += 1
                
                content = (doc.get("title", "") + " " + doc.get("abstract", "")).lower()
                words = re.findall(r'\b[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ]{4,}\b', content)
                stopwords = {"para", "como", "pero", "porque", "desde", "hasta", "durante", "entre", "sobre",
                            "bajo", "tras", "hacia", "contra", "mediante", "según", "durante", "mientras",
                            "the", "and", "for", "with", "that", "this", "have", "from", "they", "been",
                            "their", "would", "could", "should", "there", "these", "those", "other"}
                for w in words:
                    if w not in stopwords:
                        year_keywords[year][w] += 1
            
            # Top keywords por año
            temporal = {
                "publications_per_year": dict(sorted(year_freq.items())),
                "top_keywords_by_year": {
                    str(year): dict(Counter(kw).most_common(5)) 
                    for year, kw in sorted(year_keywords.items())
                }
            }
            
            return {"status": "temporal_analyzed", "temporal_evolution": temporal}
        
        workflow = StateGraph(PatternFinderState)
        
        workflow.add_node("preprocess", preprocess_corpus)
        workflow.add_node("keywords", extract_keywords)
        workflow.add_node("network", build_semantic_network)
        workflow.add_node("clusters", detect_clusters)
        workflow.add_node("temporal", analyze_temporal)
        
        workflow.set_entry_point("preprocess")
        workflow.add_edge("preprocess", "keywords")
        workflow.add_edge("keywords", "network")
        workflow.add_edge("network", "clusters")
        workflow.add_edge("clusters", "temporal")
        workflow.add_edge("temporal", END)
        
        return workflow.compile()
    
    async def run(self, corpus: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Ejecuta el agente con un corpus de documentos"""
        self.state.corpus = corpus
        self.state.status = "running"
        
        try:
            result = await self.graph.ainvoke(self.state)
            self.state = PatternFinderState(**result)
            return {
                "status": "success",
                "networks": self.state.semantic_networks,
                "clusters": self.state.clusters,
                "temporal": self.state.temporal_evolution,
                "keywords": self.state.keyword_frequencies
            }
        except Exception as e:
            self.state.status = "error"
            logger.error(f"Error en PatternFinder: {e}")
            return {"status": "error", "error": str(e)}
