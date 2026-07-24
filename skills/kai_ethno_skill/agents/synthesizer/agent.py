"""
Synthesizer Agent - Tejedor de Sentidos
Agente especializado en integración analítica y triangulación
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from collections import defaultdict
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SynthesizerState(BaseModel):
    """Estado del agente Synthesizer"""
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    coded_data: List[Dict[str, Any]] = Field(default_factory=list)
    patterns: Dict[str, Any] = Field(default_factory=dict)
    triangulation_matrix: Dict[str, Any] = Field(default_factory=dict)
    synthesis_report: Optional[Dict[str, Any]] = None
    contradictions: List[Dict[str, Any]] = Field(default_factory=list)
    status: str = "idle"


class SynthesizerAgent:
    """
    Agente Synthesizer - Especialista en integración analítica
    
    Capacidades:
    - Triangulación de fuentes múltiples
    - Método comparativo constante (Glaser & Strauss)
    - Grounded Theory (codificación abierta, axial, selectiva)
    - Detección de contradicciones y gaps
    - Integración cuanti-cuali
    """
    
    name = "synthesizer"
    description = "Tejedor de Sentidos - Integración analítica y triangulación"
    
    def __init__(self, llm_service: Any = None):
        self.llm = llm_service
        self.state = SynthesizerState()
        self.graph = self._build_graph()

    def _flatten_sources(self, sources: Any) -> List[Dict[str, Any]]:
        flat = []
        if isinstance(sources, list):
            for item in sources:
                flat.extend(self._flatten_sources(item))
        elif isinstance(sources, dict):
            # Si el diccionario contiene una lista de documentos/fuentes
            nested = sources.get("documents") or sources.get("sources") or sources.get("collected_docs")
            if nested and isinstance(nested, list):
                flat.extend(self._flatten_sources(nested))
            else:
                flat.append(sources)
        return [item for item in flat if isinstance(item, dict)]

    def _load_sources(self, state: SynthesizerState) -> Dict[str, Any]:
        """Carga y normaliza todas las fuentes"""
        source_index = {}
        for i, source in enumerate(state.sources):
            if not isinstance(source, dict):
                continue
            key = source.get("doi") or source.get("url") or f"source_{i}"
            source_index[key] = {
                "index": i,
                "title": source.get("title", ""),
                "authors": source.get("authors", []),
                "year": source.get("year"),
                "abstract": source.get("abstract", "")[:500],
                "type": source.get("type", ""),
                "source_db": source.get("source", ""),
                "quality_score": source.get("quality_score", 0.5)
            }
        
        return {"status": "sources_loaded", "source_index": source_index}
    
    def _identify_themes(self, state: SynthesizerState) -> Dict[str, Any]:
        """Identifica temas transversales"""
        theme_evidence = defaultdict(list)
        
        for source in state.sources:
            if not isinstance(source, dict):
                continue
            abstract = str(source.get("abstract", "")).lower()
            title = str(source.get("title", "")).lower()
            combined = title + " " + abstract
            
            anthropology_themes = {
                "identidad": ["identidad", "identity", "identidades", "self", "yo", "sí mismo"],
                "poder": ["poder", "power", "dominación", "hegemonía", "hegemony", "dominance"],
                "cultura": ["cultura", "culture", "cultural", "prácticas", "practices", "simbólico", "symbolic"],
                "género": ["género", "gender", "mujer", "woman", "femenino", "masculino", "feminist"],
                "desigualdad": ["desigualdad", "inequality", "desigualdades", "brecha", "gap", "exclusión"],
                "movilidad": ["movilidad", "mobility", "migración", "migration", "desplazamiento", "diaspora"],
                "tecnología": ["tecnología", "technology", "digital", "redes sociales", "plataforma", "platform"],
                "salud": ["salud", "health", "enfermedad", "disease", "medicina", "medicine", "cuidado"],
                "educación": ["educación", "education", "escuela", "school", "aprendizaje", "learning"],
                "ambiente": ["ambiente", "environment", "clima", "climate", "territorio", "territory"]
            }
            
            for theme, keywords in anthropology_themes.items():
                for kw in keywords:
                    if kw in combined:
                        theme_evidence[theme].append({
                            "source": source.get("title", "")[:60],
                            "year": source.get("year"),
                            "match": kw
                        })
                        break
        
        significant_themes = {k: v for k, v in theme_evidence.items() if len(v) >= 2}
        return {"status": "themes_identified", "patterns": {"themes": significant_themes}}
    
    def _triangulate(self, state: SynthesizerState) -> Dict[str, Any]:
        """Realiza triangulación de fuentes"""
        matrix = {
            "by_source_type": defaultdict(int),
            "by_year": defaultdict(int),
            "by_database": defaultdict(int),
            "by_quality": {"high": 0, "medium": 0, "low": 0}
        }
        
        for source in state.sources:
            if not isinstance(source, dict):
                continue
            stype = source.get("type", "unknown")
            matrix["by_source_type"][stype] += 1
            
            year = source.get("year")
            if year:
                matrix["by_year"][str(year)] += 1
            
            db = source.get("source", "unknown")
            matrix["by_database"][db] += 1
            
            score = source.get("quality_score", 0.5)
            if score >= 0.7:
                matrix["by_quality"]["high"] += 1
            elif score >= 0.4:
                matrix["by_quality"]["medium"] += 1
            else:
                matrix["by_quality"]["low"] += 1
        
        matrix["by_source_type"] = dict(matrix["by_source_type"])
        matrix["by_year"] = dict(matrix["by_year"])
        matrix["by_database"] = dict(matrix["by_database"])
        
        return {"status": "triangulated", "triangulation_matrix": matrix}
    
    def _detect_contradictions(self, state: SynthesizerState) -> Dict[str, Any]:
        """Detecta contradicciones entre fuentes"""
        contradictions = []
        opposition_pairs = [
            ("aumenta", "disminuye"), ("crece", "decrece"), ("positivo", "negativo"),
            ("beneficio", "riesgo"), ("avance", "retroceso"), ("inclusión", "exclusión"),
            ("moderno", "tradicional"), ("global", "local"), ("central", "periférico")
        ]
        
        valid_sources = [s for s in state.sources if isinstance(s, dict)]
        for i, source_a in enumerate(valid_sources):
            for j, source_b in enumerate(valid_sources):
                if i >= j:
                    continue
                text_a = str(source_a.get("title", "")) + " " + str(source_a.get("abstract", ""))
                text_b = str(source_b.get("title", "")) + " " + str(source_b.get("abstract", ""))
                text_a_low = text_a.lower()
                text_b_low = text_b.lower()
                
                for pos, neg in opposition_pairs:
                    if (pos in text_a_low and neg in text_b_low) or (neg in text_a_low and pos in text_b_low):
                        contradictions.append({
                            "source_a": source_a.get("title", "")[:50],
                            "source_b": source_b.get("title", "")[:50],
                            "opposition": f"{pos} vs {neg}",
                            "severity": "moderate"
                        })
                        break
        
        years = sorted(set(s.get("year") for s in valid_sources if s.get("year")))
        gaps = []
        if len(years) > 1:
            for i in range(len(years) - 1):
                if years[i+1] - years[i] > 3:
                    gaps.append(f"{years[i]}-{years[i+1]}")
        
        return {
            "status": "contradictions_detected",
            "contradictions": contradictions[:20],
            "temporal_gaps": gaps
        }
    
    def _generate_synthesis(self, state: SynthesizerState) -> Dict[str, Any]:
        """Genera reporte de síntesis final"""
        valid_sources = [s for s in state.sources if isinstance(s, dict)]
        total_sources = len(valid_sources)
        themes = state.patterns.get("themes", {}) if isinstance(state.patterns, dict) else {}
        contradictions = state.contradictions
        
        main_themes = sorted(themes.items(), key=lambda x: len(x[1]) if isinstance(x[1], list) else 1, reverse=True)[:5]
        
        synthesis = {
            "total_sources_analyzed": total_sources,
            "main_themes": [{"theme": t, "evidence_count": len(ev) if isinstance(ev, list) else 1} for t, ev in main_themes],
            "contradictions_found": len(contradictions),
            "temporal_coverage": {
                "earliest": min((s.get("year") for s in valid_sources if s.get("year")), default=None),
                "latest": max((s.get("year") for s in valid_sources if s.get("year")), default=None)
            },
            "source_diversity": {
                "databases": list(set(s.get("source", "") for s in valid_sources if s.get("source"))),
                "types": list(set(s.get("type", "") for s in valid_sources if s.get("type")))
            },
            "confidence_score": self._calculate_confidence(state),
            "recommendations": self._generate_recommendations(state)
        }
        
        return {"status": "synthesis_complete", "synthesis_report": synthesis}

    def _build_graph(self) -> StateGraph:
        """Construye el grafo de LangGraph para el flujo del agente"""
        workflow = StateGraph(SynthesizerState)
        
        workflow.add_node("load", self._load_sources)
        workflow.add_node("identify_themes", self._identify_themes)
        workflow.add_node("triangulate", self._triangulate)
        workflow.add_node("contradictions", self._detect_contradictions)
        workflow.add_node("synthesize", self._generate_synthesis)
        
        workflow.set_entry_point("load")
        workflow.add_edge("load", "identify_themes")
        workflow.add_edge("identify_themes", "triangulate")
        workflow.add_edge("triangulate", "contradictions")
        workflow.add_edge("contradictions", "synthesize")
        workflow.add_edge("synthesize", END)
        
        return workflow.compile()
    
    def _calculate_confidence(self, state: SynthesizerState) -> float:
        """Calcula score de confianza de la síntesis"""
        score = 0.0
        
        # Cantidad de fuentes
        n = len(state.sources)
        if n >= 20:
            score += 0.4
        elif n >= 10:
            score += 0.3
        elif n >= 5:
            score += 0.2
        
        # Diversidad de fuentes
        databases = set(s.get("source", "") for s in state.sources)
        if len(databases) >= 3:
            score += 0.2
        elif len(databases) >= 2:
            score += 0.1
        
        # Temas identificados
        themes = state.patterns.get("themes", {})
        if len(themes) >= 5:
            score += 0.2
        elif len(themes) >= 2:
            score += 0.1
        
        # Calidad promedio
        avg_quality = sum(s.get("quality_score", 0.5) for s in state.sources) / max(n, 1)
        score += avg_quality * 0.2
        
        return min(score, 1.0)
    
    def _generate_recommendations(self, state: SynthesizerState) -> List[str]:
        """Genera recomendaciones basadas en el análisis"""
        recs = []
        
        n = len(state.sources)
        if n < 10:
            recs.append("Ampliar búsqueda bibliográfica: menos de 10 fuentes identificadas")
        
        databases = set(s.get("source", "") for s in state.sources)
        if len(databases) < 2:
            recs.append("Diversificar bases de datos para mayor cobertura")
        
        contradictions = state.contradictions
        if len(contradictions) > 5:
            recs.append("Explorar las contradicciones identificadas como oportunidad analítica")
        
        gaps = state.contradictions.get("temporal_gaps", []) if isinstance(state.contradictions, dict) else []
        if gaps:
            recs.append(f"Completar periodos con baja producción: {', '.join(gaps[:3])}")
        
        if not recs:
            recs.append("Base de datos suficiente para análisis de triangulación")
        
        return recs
    
    async def run(self, sources: List[Dict[str, Any]],
                  coded_data: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Ejecuta el agente con fuentes y datos codificados
        
        Args:
            sources: Lista de fuentes bibliográficas
            coded_data: Datos pre-codificados de otros agentes
        
        Returns:
            Dict con reporte de síntesis y triangulación
        """
        if isinstance(sources, dict):
            src_list = (
                sources.get("documents")
                or sources.get("sources")
                or sources.get("collected_docs")
                or [sources]
            )
        elif isinstance(sources, list):
            src_list = sources
        elif sources is not None:
            src_list = [sources]
        else:
            src_list = []

        if isinstance(coded_data, dict):
            coded_list = coded_data.get("clusters") or coded_data.get("coded_segments") or [coded_data]
        elif isinstance(coded_data, list):
            coded_list = coded_data
        elif coded_data is not None:
            coded_list = [coded_data]
        else:
            coded_list = []

        self.state.sources = self._flatten_sources(src_list)
        self.state.coded_data = coded_list
        self.state.status = "running"
        
        try:
            result = await self.graph.ainvoke(self.state)
            self.state = SynthesizerState(**result)
            return {
                "status": "success",
                "synthesis": self.state.synthesis_report,
                "patterns": self.state.patterns,
                "contradictions": self.state.contradictions,
                "triangulation": self.state.triangulation_matrix
            }
        except Exception as e:
            self.state.status = "error"
            logger.error(f"Error en Synthesizer: {e}")
            return {"status": "error", "error": str(e)}

    async def synthesize(self, patterns: Any = None, sources: Any = None, **kwargs: Any) -> Dict[str, Any]:
        """
        Método de síntesis que acepta patrones y fuentes (usado por orchestrator y scripts).
        """
        return await self.run(sources=sources, coded_data=patterns)
    
    async def apply_grounded_theory(self, data: List[str]) -> Dict[str, Any]:
        """Aplica Grounded Theory a un conjunto de datos"""
        # Codificación abierta
        open_codes = defaultdict(list)
        for text in data:
            sentences = text.split('.')
            for sent in sentences:
                words = sent.lower().split()
                for w in words:
                    if len(w) > 4 and w not in {"para", "como", "pero", "porque", "desde", "hasta"}:
                        open_codes[w].append(sent.strip())
        
        # Codificación axial (agrupar códigos relacionados)
        axial_codes = {}
        for code, examples in open_codes.items():
            if len(examples) >= 2:
                axial_codes[code] = {
                    "frequency": len(examples),
                    "examples": examples[:3]
                }
        
        # Codificación selectiva (tema central)
        sorted_codes = sorted(axial_codes.items(), key=lambda x: x[1]["frequency"], reverse=True)
        core_category = sorted_codes[0] if sorted_codes else ("undetermined", {"frequency": 0})
        
        return {
            "method": "grounded_theory",
            "open_codes_count": len(open_codes),
            "axial_codes": dict(list(sorted_codes)[:10]),
            "core_category": core_category[0],
            "saturation_level": min(len(open_codes) / 50, 1.0)
        }
    
    async def compare_sources(self, source_a: Dict, source_b: Dict) -> Dict[str, Any]:
        """Compara dos fuentes específicas"""
        abstract_a = source_a.get("abstract", "")
        abstract_b = source_b.get("abstract", "")
        
        # Comparación por palabras compartidas
        words_a = set(re.findall(r'\b[a-zA-Z]{4,}\b', abstract_a.lower()))
        words_b = set(re.findall(r'\b[a-zA-Z]{4,}\b', abstract_b.lower()))
        
        shared = words_a & words_b
        unique_a = words_a - words_b
        unique_b = words_b - words_a
        
        jaccard = len(shared) / len(words_a | words_b) if (words_a | words_b) else 0.0
        
        return {
            "source_a": source_a.get("title", "")[:50],
            "source_b": source_b.get("title", "")[:50],
            "shared_terms": len(shared),
            "unique_to_a": len(unique_a),
            "unique_to_b": len(unique_b),
            "jaccard_similarity": round(jaccard, 3),
            "shared_terms_list": list(shared)[:20]
        }
    
    def get_synthesis_summary(self) -> str:
        return f"Synthesizer: {len(self.state.sources)} fuentes analizadas, {len(self.state.patterns.get('themes', {}))} temas, {len(self.state.contradictions)} contradicciones"
