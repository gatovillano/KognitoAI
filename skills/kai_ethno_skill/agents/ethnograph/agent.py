"""
Ethnograph Agent - Etnógrafo Digital
Agente especializado en procesamiento de materiales etnográficos
"""

import asyncio
import re
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class EthnographState(BaseModel):
    """Estado del agente Ethnograph"""
    raw_materials: List[Dict[str, Any]] = Field(default_factory=list)
    processed_data: List[Dict[str, Any]] = Field(default_factory=list)
    coded_segments: List[Dict[str, Any]] = Field(default_factory=list)
    themes: Dict[str, List[str]] = Field(default_factory=dict)
    analysis_type: str = "mixed_methods"
    status: str = "idle"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EthnographAgent:
    """
    Agente Ethnograph - Especialista en análisis etnográfico
    
    Capacidades:
    - Análisis del discurso (Fairclough, van Dijk)
    - Teoría del Actor-Red (Latour, Callon)
    - Etnografía de la práctica (Schatzki, Reckwitz)
    - Análisis narrativo (Riessman)
    - Codificación temática (Braun & Clarke)
    - Detección de PII y enmascaramiento ético
    """
    
    name = "ethnograph"
    description = "Etnógrafo Digital - Procesamiento de materiales etnográficos"
    
    def __init__(self, llm_service: Any = None):
        self.llm = llm_service
        self.graph = self._build_graph()
        self.state = EthnographState()
    
    def _build_graph(self) -> StateGraph:
        """Construye el grafo de LangGraph para el flujo del agente"""
        
        def ingest_materials(state: EthnographState) -> Dict[str, Any]:
            """Ingiere y normaliza materiales etnográficos"""
            processed = []
            for material in state.raw_materials:
                text = material.get("text", material.get("content", ""))
                source_type = material.get("type", "unknown")
                
                # Normalizar
                normalized = {
                    "original": text,
                    "normalized": self._normalize_text(text),
                    "source_type": source_type,
                    "length": len(text),
                    "word_count": len(text.split()),
                    "processed_at": datetime.now().isoformat(),
                    "metadata": material.get("metadata", {})
                }
                processed.append(normalized)
            
            return {"status": "ingested", "processed_data": processed}
        
        def detect_pii(state: EthnographState) -> Dict[str, Any]:
            """Detecta y enmascara información personal identificable"""
            pii_patterns = {
                "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                "phone": r'\b(?:\+?(\d{1,3}))?[-.\s]?(\(?\d{2,4}\)?)[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b',
                "dni_nie": r'\b\d{8}[A-HJ-NP-TV-Z]\b',
                "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
                "ip_address": r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
                "credit_card": r'\b(?:\d{4}[-\s]?){3}\d{4}\b'
            }
            
            redacted_data = []
            pii_count = 0
            
            for item in state.processed_data:
                text = item["normalized"]
                original = item["original"]
                findings = {}
                
                for pii_type, pattern in pii_patterns.items():
                    matches = re.findall(pattern, text, re.IGNORECASE)
                    if matches:
                        findings[pii_type] = len(matches)
                        pii_count += len(matches)
                        # Enmascarar
                        text = re.sub(pattern, f"[{pii_type.upper()}_REDACTED]", text, flags=re.IGNORECASE)
                
                redacted_item = {
                    **item,
                    "redacted_text": text,
                    "pii_findings": findings,
                    "pii_count": pii_count,
                    "is_redacted": bool(findings)
                }
                redacted_data.append(redacted_item)
            
            return {
                "status": "pii_detected",
                "processed_data": redacted_data,
                "total_pii_instances": pii_count
            }
        
        def code_themes(state: EthnographState) -> Dict[str, Any]:
            """Codifica temas y categorías analíticas"""
            all_texts = [item["redacted_text"] for item in state.processed_data]
            
            # Extracción de temas por frecuencia de términos significativos
            word_freq = {}
            for text in all_texts:
                words = re.findall(r'\b[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ]{4,}\b', text.lower())
                stopwords = {"para", "como", "pero", "porque", "desde", "hasta", "durante", "entre", "sobre", 
                            "bajo", "tras", "hacia", "contra", "mediante", "según", "durante", "mientras",
                            "the", "and", "for", "with", "that", "this", "have", "from", "they", "been",
                            "their", "would", "could", "should", "there", "these", "those", "other"}
                for w in words:
                    if w not in stopwords and len(w) > 3:
                        word_freq[w] = word_freq.get(w, 0) + 1
            
            # Top temas
            sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
            top_themes = {word: count for word, count in sorted_words[:20]}
            
            # Codificación de segmentos
            coded_segments = []
            for item in state.processed_data:
                text = item["redacted_text"]
                sentences = re.split(r'(?<=[.!?])\s+', text)
                for sent in sentences:
                    sent = sent.strip()
                    if len(sent) < 10:
                        continue
                    # Asignar temas basados en palabras clave
                    codes = []
                    for theme in top_themes.keys():
                        if theme in sent.lower():
                            codes.append(theme)
                    if codes:
                        coded_segments.append({
                            "text": sent,
                            "codes": codes[:3],
                            "source_id": id(item)
                        })
            
            state.themes = top_themes
            return {
                "status": "coded",
                "themes": top_themes,
                "coded_segments": coded_segments
            }
        
        def analyze_discourse(state: EthnographState) -> Dict[str, Any]:
            """Aplica análisis del discurso según framework seleccionado"""
            # Análisis simplificado: identificación de marcas lingüísticas
            discourse_markers = {
                "modalidad_deóntica": re.compile(r'\b(debe|debería|tiene que|es necesario|obligatorio|prohibido)\b', re.I),
                "modalidad_epistémica": re.compile(r'\b(parece|probablemente|posiblemente|tal vez|quizás|supongo)\b', re.I),
                "referencias_actorales": re.compile(r'\b(él|ella|ellos|ellas|el usuario|la usuaria|los participantes)\b', re.I),
                "tecnicismos": re.compile(r'\b([A-Z]{2,}|[a-z]+ción|[a-z]+dad|[a-z]+mente)\b'),
            }
            
            discourse_analysis = {}
            for item in state.processed_data:
                text = item.get("redacted_text", "")
                findings = {}
                for category, pattern in discourse_markers.items():
                    matches = pattern.findall(text)
                    findings[category] = len(matches)
                discourse_analysis[id(item)] = findings
            
            return {
                "status": "discourse_analyzed",
                "discourse_analysis": discourse_analysis,
                "framework": "fairclough_inspired"
            }
        
        def map_actors(state: EthnographState) -> Dict[str, Any]:
            """Mapea actores y redes (ANT simplificada)"""
            # Identificación de actores por sustantivos comunes y nombres propios
            actor_mentions = {}
            for item in state.processed_data:
                text = item.get("redacted_text", "")
                # Buscar sustantivos comunes que podrían ser actantes
                actors = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', text)
                for actor in actors:
                    if len(actor) > 2 and actor not in {"The", "This", "That", "These", "Those"}:
                        actor_mentions[actor] = actor_mentions.get(actor, 0) + 1
            
            # Filtrar actores con al menos 2 menciones
            significant_actors = {k: v for k, v in actor_mentions.items() if v >= 2}
            
            return {
                "status": "actors_mapped",
                "actors": significant_actors,
                "total_unique_actors": len(significant_actors)
            }
        
        # Construir grafo con rutas condicionales
        workflow = StateGraph(EthnographState)
        
        workflow.add_node("ingest", ingest_materials)
        workflow.add_node("detect_pii", detect_pii)
        workflow.add_node("code", code_themes)
        workflow.add_node("discourse", analyze_discourse)
        workflow.add_node("map_actors", map_actors)
        
        workflow.set_entry_point("ingest")
        workflow.add_edge("ingest", "detect_pii")
        
        # Rama condicional según tipo de análisis
        workflow.add_conditional_edges(
            "detect_pii",
            lambda state: state.analysis_type,
            {
                "discourse_analysis": "discourse",
                "actor_network": "map_actors",
                "mixed_methods": "code"
            }
        )
        
        workflow.add_edge("code", END)
        workflow.add_edge("discourse", END)
        workflow.add_edge("map_actors", END)
        
        return workflow.compile()
    
    async def run(self, materials: List[Dict[str, Any]],
                  analysis_type: str = "mixed_methods") -> Dict[str, Any]:
        """
        Ejecuta el agente con materiales etnográficos
        
        Args:
            materials: Lista de materiales (transcripciones, notas, observaciones)
            analysis_type: Tipo de análisis a aplicar
        
        Returns:
            Dict con materiales procesados y analysis metadata
        """
        self.state.raw_materials = materials
        self.state.analysis_type = analysis_type
        self.state.status = "running"
        
        try:
            result = await self.graph.ainvoke(self.state)
            self.state = EthnographState(**result)
            return {
                "status": "success",
                "processed_materials": self.state.processed_data,
                "coded_segments": self.state.coded_segments,
                "themes": self.state.themes,
                "metadata": self.state.metadata
            }
        except Exception as e:
            self.state.status = "error"
            logger.error(f"Error en Ethnograph: {e}")
            return {"status": "error", "error": str(e)}
    
    def _normalize_text(self, text: str) -> str:
        """Normalización básica de texto"""
        # Eliminar espacios múltiples, saltos de línea excesivos
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        # Eliminar caracteres no imprimibles excepto newline
        text = re.sub(r'[^\x20-\x7E\xA0-\xFF\u0100-\u017F\u2010-\u2027\u2030-\u205E\u2070-\u209F\u20A0-\u20CF\u2100-\u214F\u2150-\u218F\u2190-\u21FF\u2200-\u22FF\uFB00-\uFB4F\uFE30-\uFE4F\uFF00-\uFFEF\n]', '', text)
        return text.strip()
    
    async def analyze_transcription(self, transcription: str,
                                    context: Dict = None) -> Dict[str, Any]:
        """Analiza una transcripción de entrevista/observación"""
        material = {
            "text": transcription,
            "type": "transcription",
            "metadata": context or {}
        }
        return await self.run([material], analysis_type="mixed_methods")
    
    async def code_themes_braun_clarke(self, text_segments: List[str]) -> Dict[str, List[str]]:
        """Codificación temática siguiendo Braun & Clarke (2006) - versión simplificada"""
        # Fase 1-3: codificación abierta, axial, selectiva (simplificada)
        all_themes = {}
        for segment in text_segments:
            words = re.findall(r'\b[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ]{4,}\b', segment.lower())
            stopwords = {"para", "como", "pero", "porque", "desde", "hasta", "durante", "entre", "sobre",
                        "bajo", "tras", "hacia", "contra", "mediante", "según", "durante", "mientras",
                        "the", "and", "for", "with", "that", "this", "have", "from", "they", "been",
                        "their", "would", "could", "should", "there", "these", "those", "other"}
            for w in words:
                if w not in stopwords:
                    all_themes[w] = all_themes.get(w, 0) + 1
        
        # Seleccionar top temas
        sorted_themes = sorted(all_themes.items(), key=lambda x: x[1], reverse=True)
        selected = {theme: [theme] for theme, _ in sorted_themes[:15]}
        return selected
    
    def get_analysis_summary(self) -> str:
        """Resumen del análisis realizado"""
        return f"Ethnograph: {len(self.state.coded_segments)} segmentos codificados, {len(self.state.themes)} temas identificados, {self.state.metadata.get('total_pii_instances', 0)} PII detectados"
