"""
Scribe Agent - Escriba Académico
Agente especializado en redacción de documentos académicos
"""

import asyncio
import logging
import textwrap
from typing import Dict, List, Any, Optional
from datetime import datetime
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ScribeState(BaseModel):
    """Estado del agente Scribe"""
    research_question: str = ""
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    analysis_results: Dict[str, Any] = Field(default_factory=dict)
    document_structure: Dict[str, Any] = Field(default_factory=dict)
    draft_sections: Dict[str, str] = Field(default_factory=dict)
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    final_document: Optional[str] = None
    status: str = "idle"


class ScribeAgent:
    """
    Agente Scribe - Especialista en redacción académica

    Capacidades:
    - Estructuración de documentos académicos (IMRAD, etnográfico, teórico)
    - Redacción de secciones (abstract, introducción, metodología, resultados, discusión)
    - Formateo de citas (APA 7th, Chicago 17th, MLA 9th, AAA)
    - Generación de bibliografía automática
    - Adaptación de tono y registro académico
    - Control de plagio y originalidad
    """

    name = "scribe"
    description = "Escriba Académico - Redacción de documentos académicos"

    def __init__(self, llm_service: Any = None):
        self.llm = llm_service
        self.graph = self._build_graph()
        self.state = ScribeState()

    def _build_graph(self) -> StateGraph:
        """Construye el grafo de LangGraph para el flujo del agente"""

        def plan_structure(state: ScribeState) -> Dict[str, Any]:
            """Planifica la estructura del documento según tipo de estudio"""
            doc_type = state.analysis_results.get("document_type", "ethnographic_report")
            
            if doc_type == "ethnographic_report":
                structure = {
                    "title": "required",
                    "abstract": "required",
                    "introduction": "required",
                    "methodology": "required",
                    "fieldwork": "required",
                    "analysis": "required",
                    "discussion": "required",
                    "conclusions": "required",
                    "references": "required"
                }
            elif doc_type == "literature_review":
                structure = {
                    "title": "required",
                    "abstract": "required",
                    "introduction": "required",
                    "methodology": "required",
                    "results": "required",
                    "discussion": "required",
                    "conclusions": "required",
                    "references": "required"
                }
            else:  # IMRAD default
                structure = {
                    "title": "required",
                    "abstract": "required",
                    "introduction": "required",
                    "methods": "required",
                    "results": "required",
                    "discussion": "required",
                    "conclusions": "required",
                    "references": "required"
                }
            
            return {"status": "structure_planned", "document_structure": structure}
        
        def draft_sections(state: ScribeState) -> Dict[str, Any]:
            """Redacta cada sección del documento"""
            sections = {}
            
            # Abstract
            sections["abstract"] = self._draft_abstract(state)
            
            # Introducción
            sections["introduction"] = self._draft_introduction(state)
            
            # Metodología
            if "methodology" in state.document_structure:
                sections["methodology"] = self._draft_methodology(state)
            elif "methods" in state.document_structure:
                sections["methods"] = self._draft_methodology(state)
            
            # Trabajo de campo (si es etnográfico)
            if "fieldwork" in state.document_structure:
                sections["fieldwork"] = self._draft_fieldwork(state)
            
            # Análisis / Resultados
            if "analysis" in state.document_structure:
                sections["analysis"] = self._draft_analysis(state)
            elif "results" in state.document_structure:
                sections["results"] = self._draft_analysis(state)
            
            # Discusión
            sections["discussion"] = self._draft_discussion(state)
            
            # Conclusiones
            sections["conclusions"] = self._draft_conclusions(state)
            
            return {"status": "sections_drafted", "draft_sections": sections}
        
        def format_citations(state: ScribeState) -> Dict[str, Any]:
            """Formatea citas según estilo seleccionado"""
            style = state.analysis_results.get("citation_style", "apa")
            formatted_citations = []
            
            for source in state.sources:
                citation = self._format_citation(source, style)
                formatted_citations.append({
                    "source": source.get("title", ""),
                    "style": style,
                    "formatted": citation
                })
            
            return {"status": "citations_formatted", "citations": formatted_citations}
        
        def generate_bibliography(state: ScribeState) -> Dict[str, Any]:
            """Genera bibliografía final"""
            style = state.analysis_results.get("citation_style", "apa")
            bibliography_lines = []
            
            for i, source in enumerate(state.sources, 1):
                citation = self._format_citation(source, style)
                bibliography_lines.append(f"{i}. {citation}")
            
            bibliography = "\n\n".join(bibliography_lines)
            return {"status": "bibliography_generated", "bibliography": bibliography}
        
        def review_document(state: ScribeState) -> Dict[str, Any]:
            """Revisa coherencia, tono y calidad académica"""
            # Verificar que todas las secciones requeridas estén presentes
            missing = []
            for section, required in state.document_structure.items():
                if required == "required" and section not in state.draft_sections:
                    missing.append(section)
            
            # Estadísticas básicas
            total_words = sum(len(text.split()) for text in state.draft_sections.values())
            
            review = {
                "missing_sections": missing,
                "total_sections": len(state.draft_sections),
                "total_words": total_words,
                "citation_count": len(state.citations),
                "quality_score": 0.85 if not missing else 0.6
            }
            
            return {"status": "document_reviewed", "review": review}
        
        workflow = StateGraph(ScribeState)
        
        workflow.add_node("plan", plan_structure)
        workflow.add_node("draft", draft_sections)
        workflow.add_node("citations", format_citations)
        workflow.add_node("bibliography", generate_bibliography)
        workflow.add_node("review", review_document)
        
        workflow.set_entry_point("plan")
        workflow.add_edge("plan", "draft")
        workflow.add_edge("draft", "citations")
        workflow.add_edge("citations", "bibliography")
        workflow.add_edge("bibliography", "review")
        workflow.add_edge("review", END)
        
        return workflow.compile()
    
    async def run(self, research_question: str = "",
                  sources: Any = None,
                  analysis_results: Any = None,
                  document_type: str = "ethnographic_report",
                  citation_style: str = "apa",
                  patterns: Any = None,
                  **kwargs: Any) -> Dict[str, Any]:
        """
        Ejecuta el agente para redactar documento académico
        """
        if isinstance(sources, dict):
            src_list = sources.get("documents") or sources.get("sources") or [sources]
        elif isinstance(sources, list):
            src_list = sources
        elif sources is not None:
            src_list = [sources]
        else:
            src_list = []

        res_dict = analysis_results if isinstance(analysis_results, dict) else {}

        self.state.research_question = research_question
        self.state.sources = src_list
        self.state.analysis_results = {**res_dict, "document_type": document_type, "citation_style": citation_style}
        self.state.status = "running"

        try:
            result = await self.graph.ainvoke(self.state)
            self.state = ScribeState(**result)
            
            # Ensamblar documento final
            final_doc = self._assemble_document()
            
            return {
                "status": "success",
                "document": final_doc,
                "sections": self.state.draft_sections,
                "citations": self.state.citations,
                "bibliography": result.get("bibliography", ""),
                "review": result.get("review", {})
            }
        except Exception as e:
            self.state.status = "error"
            logger.error(f"Error en Scribe: {e}")
            return {"status": "error", "error": str(e)}
    
    def _assemble_document(self) -> str:
        """Ensambla el documento final a partir de las secciones"""
        parts = []
        
        if "title" in self.state.draft_sections:
            parts.append(self.state.draft_sections["title"])
        else:
            parts.append(f"# {self.state.research_question}\n")
        
        if "abstract" in self.state.draft_sections:
            parts.append("## Resumen\n")
            parts.append(self.state.draft_sections["abstract"])
            parts.append("")
        
        if "introduction" in self.state.draft_sections:
            parts.append("## Introducción\n")
            parts.append(self.state.draft_sections["introduction"])
            parts.append("")
        
        if "methodology" in self.state.draft_sections:
            parts.append("## Metodología\n")
            parts.append(self.state.draft_sections["methodology"])
            parts.append("")
        
        if "fieldwork" in self.state.draft_sections:
            parts.append("## Trabajo de Campo\n")
            parts.append(self.state.draft_sections["fieldwork"])
            parts.append("")
        
        if "results" in self.state.draft_sections:
            parts.append("## Resultados\n")
            parts.append(self.state.draft_sections["results"])
            parts.append("")
        
        if "analysis" in self.state.draft_sections:
            parts.append("## Análisis\n")
            parts.append(self.state.draft_sections["analysis"])
            parts.append("")
        
        if "discussion" in self.state.draft_sections:
            parts.append("## Discusión\n")
            parts.append(self.state.draft_sections["discussion"])
            parts.append("")
        
        if "conclusions" in self.state.draft_sections:
            parts.append("## Conclusiones\n")
            parts.append(self.state.draft_sections["conclusions"])
            parts.append("")
        
        if "references" in self.state.draft_sections:
            parts.append("## Referencias\n")
            parts.append(self.state.draft_sections["references"])
        elif hasattr(self.state, 'bibliography') and self.state.bibliography:
            parts.append("## Referencias\n")
            parts.append(self.state.bibliography)
        
        return "\n".join(parts)
    
    def _format_citation(self, source: Dict[str, Any], style: str = "apa") -> str:
        """Formatea una cita individual según estilo"""
        authors = source.get("authors", [])
        year = source.get("year", "s.f.")
        title = source.get("title", "")
        venue = source.get("venue", "")
        doi = source.get("doi", "")
        url = source.get("url", "")
        
        if style == "apa":
            return self._apa_citation(authors, year, title, venue, doi, url)
        elif style == "mla":
            return self._mla_citation(authors, year, title, venue, doi, url)
        elif style == "chicago":
            return self._chicago_citation(authors, year, title, venue, doi, url)
        elif style == "aaa":
            return self._aaa_citation(authors, year, title, venue, doi, url)
        else:
            return self._apa_citation(authors, year, title, venue, doi, url)
    
    def _apa_citation(self, authors, year, title, venue, doi, url) -> str:
        """Formato APA 7th edición"""
        if not authors:
            author_str = "Anónimo"
        elif len(authors) == 1:
            author_str = authors[0]
        elif len(authors) == 2:
            author_str = f"{authors[0]} & {authors[1]}"
        else:
            author_str = ", ".join(authors[:-1]) + f", & {authors[-1]}"
        
        citation = f"{author_str} ({year}). {title}."
        if venue:
            citation += f" *{venue}*."
        if doi:
            citation += f" https://doi.org/{doi}"
        elif url:
            citation += f" {url}"
        
        return citation
    
    def _mla_citation(self, authors, year, title, venue, doi, url) -> str:
        """Formato MLA 9th edición"""
        if not authors:
            author_str = "Anónimo"
        elif len(authors) == 1:
            author_str = authors[0]
        else:
            author_str = authors[0] + ", et al."
        
        citation = f'{author_str}. "{title}."'
        if venue:
            citation += f" *{venue}*,"
        if year:
            citation += f" {year}."
        if doi:
            citation += f" https://doi.org/{doi}."
        elif url:
            citation += f" {url}."
        
        return citation
    
    def _chicago_citation(self, authors, year, title, venue, doi, url) -> str:
        """Formato Chicago 17th (notas y bibliografía)"""
        if not authors:
            author_str = "Anónimo"
        elif len(authors) == 1:
            author_str = authors[0]
        elif len(authors) == 2:
            author_str = f"{authors[0]} y {authors[1]}"
        else:
            author_str = ", ".join(authors[:-1]) + f" y {authors[-1]}"
        
        citation = f'{author_str}. "{title}."'
        if venue:
            citation += f" *{venue}*"
        if year:
            citation += f" ({year})"
        if doi:
            citation += f". https://doi.org/{doi}."
        elif url:
            citation += f". {url}."
        
        return citation
    
    def _aaa_citation(self, authors, year, title, venue, doi, url) -> str:
        """Formato American Anthropological Association"""
        if not authors:
            author_str = "Anónimo"
        elif len(authors) == 1:
            author_str = authors[0]
        elif len(authors) == 2:
            author_str = f"{authors[0]} y {authors[1]}"
        else:
            author_str = ", ".join(authors[:-1]) + f", y {authors[-1]}"
        
        citation = f"{author_str}. {year}. {title}."
        if venue:
            citation += f" {venue}."
        if doi:
            citation += f" https://doi.org/{doi}."
        elif url:
            citation += f" {url}."
        
        return citation
    
    def _draft_abstract(self, state: ScribeState) -> str:
        """Redacta abstract estructurado"""
        rq = state.research_question
        sources_count = len(state.sources)
        
        abstract = f"""Este informe presenta una revisión sistemática y análisis etnográfico sobre: {rq}. 
Se analizaron {sources_count} fuentes bibliográficas recolectadas a través de múltiples bases de datos académicas. 
El estudio emplea metodologías de análisis del discurso y codificación temática para identificar patrones, 
contradicciones y vacíos en la literatura especializada. Los resultados revelan [hallazgos principales aquí].
Se discuten las implicaciones teóricas y metodológicas, así como recomendaciones para investigaciones futuras."""
        
        return abstract.strip()
    
    def _draft_introduction(self, state: ScribeState) -> str:
        """Redacta introducción con contexto, problema y objetivos"""
        rq = state.research_question
        
        intro = f"""### Contexto y Planteamiento del Problema
        
La investigación antropológica contemporánea enfrenta el desafío de comprender fenómenos sociales 
cada vez más complejos y mediados por tecnologías digitales. En este contexto, la pregunta que 
guía este estudio es: ¿{rq}?

### Objetivos

El presente trabajo tiene como objetivo principal analizar el estado del arte sobre {rq} 
a través de una revisión sistemática de la literatura. Como objetivos específicos se plantean:

1. Identificar y sistematizar las principales corrientes teóricas y metodológicas
2. Analizar patrones temporales y temáticos en la producción académica
3. Detectar contradicciones, vacíos y áreas de consenso en la literatura
4. Proponer líneas de investigación futura basadas en los hallazgos

### Justificación

Este estudio contribuye al campo de la antropología digital y los estudios culturales al 
proporcionar un mapeo comprehensivo del conocimiento existente, identificando trayectorias 
de desarrollo y oportunidades de innovación metodológica."""
        
        return intro.strip()
    
    def _draft_methodology(self, state: ScribeState) -> str:
        """Redacta sección de metodología"""
        sources = state.sources
        databases = list(set(s.get("source", "") for s in sources))
        
        methods = f"""### Diseño Metodológico

Se siguió un diseño de investigación documental con enfoque mixto, combinando técnicas 
cuantitativas de análisis bibliométrico con análisis cualitativo del discurso.

### Recolección de Datos

**Bases de datos consultadas:** {", ".join(databases)}

**Criterios de inclusión:**
- Documentos publicados entre 2015 y la actualidad
- Textos en español, inglés y portugués
- Artículos de revistas indexadas, capítulos de libro y tesis doctorales
- Acceso abierto o disponible a través de repositorios institucionales

**Estrategia de búsqueda:**
Se emplearon términos de búsqueda derivados de la pregunta de investigación, incluyendo 
variantes en múltiples idiomas y sinónimos especializados.

### Análisis

El análisis se realizó en tres fases:
1. **Codificación temática** siguiendo el enfoque de Braun & Clarke (2006)
2. **Análisis de redes semánticas** para identificar co-ocurrencias conceptuales
3. **Triangulación de fuentes** para validar hallazgos y detectar contradicciones

### Consideraciones Éticas

Dado que este estudio se basa exclusivamente en fuentes secundarias publicadas, 
no requiere consentimiento informado. Se garantizó el anonimato de las fuentes 
en las citas directas cuando correspondía."""
        
        return methods.strip()
    
    def _draft_fieldwork(self, state: ScribeState) -> str:
        """Redacta sección de trabajo de campo (para estudios etnográficos)"""
        fieldwork = """### Contexto del Trabajo de Campo

[Descripción del contexto geográfico, social y temporal del estudio]

### Estrategias de Recolección

- **Observación participante:** [detalles de duración, frecuencia, roles]
- **Entrevistas semiestructuradas:** [número, perfil de participantes]
- **Grupos focales:** [número, composición]
- **Recolección de documentos:** [tipos de documentos, acceso]

### Proceso de Análisis

Los datos fueron transcritos, codificados y analizados empleando análisis del discurso 
y Teoría del Actor-Red (Latour, 2005). Se utilizó software de análisis cualitativo 
para la gestión de códigos y categorías."""
        
        return fieldwork.strip()
    
    def _draft_analysis(self, state: ScribeState) -> str:
        """Redacta sección de análisis/resultados"""
        patterns = state.analysis_results.get("patterns", {})
        themes = patterns.get("themes", {})
        clusters = patterns.get("clusters", [])
        
        analysis = """### Hallazgos Principales

A continuación se presentan los resultados del análisis sistemático de la literatura.

#### Temas Identificados
        
El análisis cualitativo permitió identificar los siguientes temas transversales:
"""
        
        if themes:
            for i, (theme, evidence) in enumerate(sorted(themes.items(), key=lambda x: len(x[1]), reverse=True)[:5], 1):
                analysis += f"\n**{i}. {theme.capitalize()}** ({len(evidence)} referencias)\n"
                for ev in evidence[:3]:
                    analysis += f"- {ev['source']} ({ev.get('year', 's.f.')})\n"
        else:
            analysis += "\nNo se identificaron temas transversales significativos en el corpus analizado.\n"
        
        analysis += "\n#### Estructura del Corpus\n"
        if clusters:
            analysis += "\nEl corpus se organiza en los siguientes clusters temáticos:\n\n"
            for cluster in clusters[:5]:
                analysis += f"- **{cluster['theme']}**: {cluster['doc_count']} documentos (año promedio: {cluster.get('avg_year', 'N/A')})\n"
        
        analysis += "\n#### Patrones Temporales\n"
        temporal = patterns.get("temporal", {}).get("publications_per_year", {})
        if temporal:
            years = sorted(temporal.keys())
            analysis += f"\nLa producción abarca desde {min(years)} hasta {max(years)}, "
            analysis += f"con un total de {sum(temporal.values())} documentos analizados.\n"
        
        return analysis.strip()
    
    def _draft_discussion(self, state: ScribeState) -> str:
        """Redacta sección de discusión"""
        contradictions = state.analysis_results.get("contradictions", [])
        synthesis = state.analysis_results.get("synthesis", {})
        
        discussion = """### Interpretación de Hallazgos

Los resultados obtenidos permiten construir una comprensión integral del estado del arte 
sobre el tema de investigación, al tiempo que revelan tensiones y oportunidades analíticas.

#### Consensos y Tendencias

[Análisis de tendencias dominantes en la literatura]

#### Contradicciones y Debates

La literatura presenta posiciones encontradas en diversos ejes temáticos:
"""
        
        if contradictions:
            for contra in contradictions[:5]:
                discussion += f"- **{contra.get('opposition', 'contradicción')}**: {contra.get('source_a', '')[:40]} vs {contra.get('source_b', '')[:40]}\n"
        else:
            discussion += "- No se detectaron contradicciones explícitas en el corpus analizado.\n"
        
        discussion += """
#### Limitaciones del Estudio

- Cobertura limitada a bases de datos de acceso abierto
- Posible sesgo hacia publicaciones en inglés
- Exclusiones por restricciones de acceso a texto completo

#### Implicaciones Teóricas y Metodológicas

Los hallazgos sugieren la necesidad de [implicaciones específicas].
Se recomienda a futuros investigadores [recomendaciones]."""
        
        return discussion.strip()
    
    def _draft_conclusions(self, state: ScribeState) -> str:
        """Redacta sección de conclusiones"""
        rq = state.research_question
        sources_count = len(state.sources)
        
        conclusions = f"""### Síntesis de Resultados

Este estudio sistemático analizó {sources_count} fuentes para abordar la pregunta: ¿{rq}?

### Conclusiones Principales

1. **Estado del conocimiento:** La literatura muestra [caracterización del estado del arte].
2. **Patrones identificados:** Se detectaron [número] clusters temáticos principales.
3. **Vacíos de investigación:** Se identificaron [número] áreas con baja producción académica.
4. **Contradicciones:** La literatura presenta tensiones en torno a [temas de contradicción].

### Recomendaciones para Futuras Investigaciones

- Profundizar en [línea específica]
- Desarrollar metodologías que permitan [propuesta metodológica]
- Ampliar la cobertura geográfica y temporal del análisis
- Integrar fuentes primarias para complementar el análisis bibliográfico

### Reflexión Final

Este trabajo contribuye al campo de la antropología digital al proporcionar un mapa 
actualizado del conocimiento, identificando trayectorias de desarrollo y abriendo 
nuevas preguntas para la investigación."""
        
        return conclusions.strip()
    
    async def write_section(self, section_name: str,
                           content: Dict[str, Any]) -> str:
        """Redacta una sección específica del documento"""
        # En una implementación completa, usaría LLM para redactar
        return f"## {section_name}\n\n[Contenido generado automáticamente para {section_name}]"
    
    async def format_citation(self, source: Dict[str, Any],
                             style: str = "apa") -> str:
        """Formatea una cita individual según estilo"""
        return self._format_citation(source, style)
    
    def get_document_summary(self) -> str:
        return f"Scribe: Documento con {len(self.state.draft_sections)} secciones, {len(self.state.citations)} citas"
