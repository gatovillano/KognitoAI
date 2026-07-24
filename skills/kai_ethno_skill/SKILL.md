---
name: kai_ethno_skill
description: Skill especializada para investigación etnográfica, antropología digital, análisis del discurso y revisiones de literatura académica.
---

# KAI-Ethno: Investigación Antropológica Aumentada

## Descripción

Skill especializada de KognitoAI para investigación etnográfica y antropológica aumentada mediante inteligencia artificial. Sistema multi-agente que automatiza la recolección bibliográfica sistemática, análisis del discurso, minería de patrones, triangulación de fuentes y generación de documentos académicos.

## Cuándo Usar Esta Skill

- Búsqueda sistemática de literatura en antropología, sociología, estudios culturales o campos afines
- Análisis de transcripciones de entrevistas, grupos focales o trabajo de campo
- Minería de patrones en corpus textuales académicos
- Generación de documentos de revisión sistemática o informes etnográficos
- Visualización de redes semánticas, nubes de palabras o análisis temporal de literatura
- Archivado y gestión de conocimiento colectivo de investigación

## Arquitectura

```
KAI Core (Orquestador)
├── Ethics Council (Veto ético)
├── Bibliomancer ──────┐
├── Ethnograph ────────┤
├── PatternFinder ─────┤
├── Synthesizer ───────┼── Pipeline de investigación
├── Visualizer ────────┤
├── Scribe ────────────┘
└── Archivist
```

## Agentes Especializados

| Agente | Función | Capacidades Principales |
|--------|---------|------------------------|
| **Bibliomancer** | Cazador de Textos | Búsqueda multi-API (Semantic Scholar, arXiv, CrossRef, SciELO, RedALyC, PubMed). Filtrado por calidad, exportación BibTeX/CSV |
| **Ethnograph** | Etnógrafo Digital | Procesamiento transcripciones, detección PII (regex), codificación temática (Braun & Clarke), análisis del discurso |
| **PatternFinder** | Detective de Patrones | Redes semánticas de co-ocurrencia, clustering temático, análisis temporal, extracción de keywords |
| **Synthesizer** | Sabio Colegiado | Triangulación de fuentes, detección de contradicciones, identificación de gaps, Grounded Theory |
| **Visualizer** | Cartógrafo Visual | Nubes de palabras, gráficos de barras, redes, líneas de tiempo, dashboards |
| **Scribe** | Escriba Académico | Redacción documentos (IMRAD, etnográfico), citas APA/MLA/Chicago/AAA, bibliografía |
| **Archivist** | Guardián de la Memoria | Indexación semántica, detección duplicados, backup JSON, búsqueda |

## Flujo de Uso

### Pipeline Completo (Recomendado)

```python
import asyncio
from orchestrator import KAIEthnoOrchestrator

async def investigate():
    orchestrator = KAIEthnoOrchestrator()
    
    result = await orchestrator.run_research(
        research_question="¿Cómo construyen los jóvenes su identidad digital en TikTok?",
        max_sources=100,
        year_range=(2020, 2025),
        include_visualizations=True,
        generate_document=True,
        document_type="ethnographic_report",
        citation_style="apa"
    )
    
    return result

# Ejecutar
result = asyncio.run(investigate())
```

### Uso Individual de Agentes

```python
from agents.bibliomancer import BibliomancerAgent
from agents.ethnograph import EthnographAgent
from agents.pattern_finder import PatternFinderAgent
from agents.synthesizer import SynthesizerAgent
from agents.visualizer import VisualizerAgent
from agents.scribe import ScribeAgent
from agents.archivist import ArchivistAgent

# 1. Búsqueda bibliográfica
biblio = BibliomancerAgent()
sources = await biblio.search(
    query="antropología digital identidad",
    max_results=50,
    year_range=(2020, 2025)
)

# 2. Procesamiento etnográfico
ethno = EthnographAgent()
processed = await ethno.process_corpus(sources)

# 3. Minería de patrones
patterns = await PatternFinderAgent().analyze(processed)

# 4. Síntesis
synthesis = await SynthesizerAgent().synthesize(patterns)

# 5. Visualizaciones
visuals = await VisualizerAgent().run({
    "keywords": patterns.get("keywords", {}),
    "networks": patterns.get("networks", []),
    "clusters": patterns.get("clusters", [])
})

# 6. Redacción
document = await ScribeAgent().run(
    research_question="Identidad digital en jóvenes",
    sources=sources,
    analysis_results=synthesis,
    document_type="ethnographic_report"
)

# 7. Archivado
archive = await ArchivistAgent().run(sources + [document])
```

## APIs Soportadas (Sin Requerir Keys)

| API | Rate Limit | Características |
|-----|------------|-----------------|
| Semantic Scholar | 100 req/5min | Abstract, citas, métricas |
| arXiv | 1 req/3s | Preprints, PDFs |
| CrossRef | 50 req/s | Metadatos, DOI, referencias |
| PubMed/NCBI | 3 req/s | Ciencias de la salud |
| SciELO | 1 req/s | Literatura iberoamericana |
| RedALyC | 1 req/s | Revistas latinoamericanas |

## Consideraciones Éticas

- **Veto automático**: Ethics Council puede bloquear operaciones riesgosas
- **Detección PII**: Anonimización automática de datos sensibles (email, teléfono, DNI, SSN, IP, tarjetas)
- **Transparencia**: Reportes de sesgos en recolección y análisis
- **Consentimiento**: Verificación de fuentes secundarias publicadas

## Ejemplos Incluidos

```bash
# Pipeline completo de investigación
python examples/basic_research.py --query "antropología urbana" --max-sources 50

# Análisis etnográfico de transcripciones
python examples/digital_ethnography.py --input ./transcripts --output ./analysis
```

## Configuración

```env
# .env (opcional para APIs públicas)
OPENAI_API_KEY=          # Mejora calidad de análisis
NEO4J_URI=bolt://localhost:7687  # Memoria de grafo
LOG_LEVEL=INFO
OUTPUT_DIR=./output
```

## Notas de Implementación

- Todos los agentes usan `langgraph` para orquestación stateful
- Estados definidos con `pydantic` para validación
- Comunicación asíncrona entre agentes (aiohttp)
- Almacenamiento local JSON + opcional Neo4j para grafos
- Sin dependencias de APIs pagas en configuración por defecto

## Troubleshooting

- **Error de importación**: Verificar que todas las carpetas tengan `__init__.py`
- **Rate limit**: Reducir `max_workers` o agregar API keys gratuitas
- **Memoria**: Aumentar `MAX_WORKERS` o usar backend Neo4j para corpus grandes
