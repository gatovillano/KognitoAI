# KAI-Ethno: Investigación Antropológica Aumentada

Skill de KognitoAI para investigación etnográfica y antropológica aumentada mediante inteligencia artificial. Sistema multi-agente que automatiza la recolección bibliográfica, análisis del discurso, minería de patrones y generación de documentos académicos.

## 🏗️ Arquitectura Multi-Agente

```
KAI Core (Orquestrador)
├── Ethics Council (Veto ético)
├── Bibliomancer ──────┐
├── Ethnograph ────────┤
├── PatternFinder ─────┤
├── Synthesizer ───────┼── Pipeline de investigación
├── Visualizer ────────┤
├── Scribe ────────────┘
└── Archivist
```

### Agentes Especializados

| Agente | Rol | Capacidades |
|--------|-----|-------------|
| **Bibliomancer** | Cazador de Textos | Recolección multi-API (Semantic Scholar, arXiv, CrossRef, SciELO, RedALyC, PubMed), filtrado por calidad, exportación BibTeX/CSV |
| **Ethnograph** | Etnógrafo Digital | Procesamiento de transcripciones, detección PII, codificación temática (Braun & Clarke), análisis del discurso, mapeo actores (ANT) |
| **PatternFinder** | Detective de Patrones | Redes semánticas, clustering temático, análisis temporal, extracción de keywords |
| **Synthesizer** | Sabio Colegiado | Triangulación de fuentes, detección de contradicciones, identificación de gaps, Grounded Theory |
| **Visualizer** | Cartógrafo Visual | Nubes de palabras, redes, líneas de tiempo, dashboards, mapas de clusters |
| **Scribe** | Escriba Académico | Redacción de documentos (IMRAD, etnográfico), citas (APA, MLA, Chicago, AAA), generación de bibliografía |
| **Archivist** | Guardián de la Memoria | Indexación semántica, detección de duplicados, backup, búsqueda |

## 🚀 Instalación

```bash
# Clonar el repositorio (si aplica)
git clone <repo-url>
cd kai-ethno-skill

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus API keys (opcional para APIs públicas)
```

## 📦 Dependencias Principales

```
aiohttp>=3.9.0          # HTTP asíncrono para APIs
langgraph>=0.2.0        # Orquestación de agentes
pydantic>=2.0.0         # Validación de estados
matplotlib>=3.7.0       # Visualizaciones
networkx>=3.0           # Grafos y redes
wordcloud>=1.9.0        # Nubes de palabras
scikit-learn>=1.3.0     # ML para clustering
nltk>=3.8.0             # Procesamiento de lenguaje
```

## ⚡ Uso Rápido

### Como Skill de KognitoAI

```python
# En tu agente KognitoAI
from skills.kai_ethno import KAIEthnoOrchestrator

orchestrator = KAIEthnoOrchestrator()

# Ejecutar investigación completa
result = await orchestrator.run_research(
    research_question="¿Cómo construyen los jóvenes su identidad digital en TikTok?",
    max_sources=100,
    include_visualizations=True,
    generate_document=True
)
```

### Como Librería Python Independiente

```python
import asyncio
from agents.bibliomancer import BibliomancerAgent
from agents.ethnograph import EthnographAgent
from agents.pattern_finder import PatternFinderAgent
from agents.synthesizer import SynthesizerAgent
from agents.visualizer import VisualizerAgent
from agents.scribe import ScribeAgent
from agents.archivist import ArchivistAgent

async def run_pipeline():
    # 1. Recolección bibliográfica
    bibliomancer = BibliomancerAgent()
    sources = await bibliomancer.search(
        query="identidad digital jóvenes redes sociales",
        max_results=50,
        year_range=(2020, 2025)
    )
    
    # 2. Procesamiento etnográfico
    ethnograph = EthnographAgent()
    processed = await ethnograph.process_corpus(sources)
    
    # 3. Minería de patrones
    pattern_finder = PatternFinderAgent()
    patterns = await pattern_finder.analyze(processed)
    
    # 4. Síntesis
    synthesizer = SynthesizerAgent()
    synthesis = await synthesizer.synthesize(patterns)
    
    # 5. Visualizaciones
    visualizer = VisualizerAgent()
    visuals = await visualizer.run({
        "keywords": patterns.get("keywords", {}),
        "networks": patterns.get("networks", []),
        "temporal": patterns.get("temporal", {}),
        "clusters": patterns.get("clusters", [])
    })
    
    # 6. Redacción
    scribe = ScribeAgent()
    document = await scribe.run(
        research_question="Identidad digital en jóvenes",
        sources=sources,
        analysis_results=synthesis,
        document_type="ethnographic_report",
        citation_style="apa"
    )
    
    # 7. Archivado
    archivist = ArchivistAgent()
    archive_result = await archivist.run(sources + [document])
    
    return {
        "sources": sources,
        "patterns": patterns,
        "synthesis": synthesis,
        "visuals": visuals,
        "document": document,
        "archive": archive_result
    }

# Ejecutar
result = asyncio.run(run_pipeline())
```

### Uso de Agentes Individuales

```python
# Solo búsqueda bibliográfica
from agents.bibliomancer import BibliomancerAgent

agent = BibliomancerAgent()
results = await agent.search("antropología digital", max_results=20)

# Solo visualizaciones
from agents.visualizer import VisualizerAgent

viz = VisualizerAgent()
visuals = await viz.run({
    "keywords": {"identidad": 50, "digital": 45, "jóvenes": 40},
    "clusters": [{"theme": "TikTok", "doc_count": 25}]
})
```

## 📖 Ejemplos Incluidos

### `examples/basic_research.py`
Pipeline completo de investigación con búsqueda bibliográfica, análisis y generación de documento.

```bash
python examples/basic_research.py --query "antropología urbana" --max-sources 50
```

### `examples/digital_ethnography.py`
Análisis etnográfico de materiales digitales con detección de PII y codificación temática.

```bash
python examples/digital_ethnography.py --input ./transcripts --output ./analysis
```

## 🔧 Configuración

### Variables de Entorno (`.env`)

```env
# APIs públicas (no requieren keys, pero recomiendo configurar)
SEMANTIC_SCHOLAR_API_KEY=
CROSSREF_MAILTO=tu@email.com
PUBMED_API_KEY=

# LLM opcional (mejora calidad de análisis)
OPENAI_API_KEY=
ANTHROPIC_API_KEY=

# Configuración general
LOG_LEVEL=INFO
OUTPUT_DIR=./output
MAX_WORKERS=5
```

### APIs Soportadas

| API | Tipo | Rate Limit | Autenticación |
|-----|------|------------|---------------|
| Semantic Scholar | Abierta | 100 req/5min | Opcional (recomendado) |
| arXiv | Abierta | 1 req/3s | No requiere |
| CrossRef | Abierta | 50 req/s | No requiere (mailto recomendado) |
| PubMed/NCBI | Abierta | 3 req/s | API key recomendada |
| SciELO | Abierta | 1 req/s | No requiere |
| RedALyC | Abierta | 1 req/s | No requiere |

## 📁 Estructura del Proyecto

```
kai_ethno_skill/
├── agents/
│   ├── bibliomancer/
│   │   ├── __init__.py
│   │   └── agent.py          # Búsqueda multi-API
│   ├── ethnograph/
│   │   ├── __init__.py
│   │   └── agent.py          # Procesamiento etnográfico
│   ├── pattern_finder/
│   │   ├── __init__.py
│   │   └── agent.py          # Minería de patrones
│   ├── synthesizer/
│   │   ├── __init__.py
│   │   └── agent.py          # Síntesis y triangulación
│   ├── visualizer/
│   │   ├── __init__.py
│   │   └── agent.py          # Visualizaciones académicas
│   ├── scribe/
│   │   ├── __init__.py
│   │   └── agent.py          # Redacción académica
│   └── archivist/
│       ├── __init__.py
│       └── agent.py          # Gestión de conocimiento
├── core/
│   ├── __init__.py
│   ├── ethics_council.py     # Revisión ética con veto
│   ├── message_bus.py        # Comunicación asíncrona
│   └── memory_manager.py     # Memoria de grafo (Neo4j)
├── examples/
│   ├── basic_research.py     # Ejemplo pipeline completo
│   └── digital_ethnography.py # Ejemplo etnografía digital
├── scripts/
│   └── orchestrator.py       # Orquestador principal
├── output/                   # Resultados generados
├── .env.example              # Template de configuración
├── requirements.txt
├── SKILL.md
└── README.md
```

## 🔒 Consideraciones Éticas

KAI-Ethno incluye un **Ethics Council** integrado que:

- Revisa automáticamente cada etapa del pipeline
- Detecta posibles sesgos en la recolección de fuentes
- Identifica contenido sensible (PII) en materiales etnográficos
- Tiene **derecho a veto** sobre cualquier operación
- Genera reportes de transparencia

### Detección de PII

El agente Ethnograph detecta automáticamente:
- Direcciones de email
- Números de teléfono
- Documentos de identidad (DNI, NIE, SSN)
- Direcciones IP
- Números de tarjetas de crédito

Estos datos son anonimizados por defecto en el procesamiento.

## 🧪 Testing

```bash
# Ejecutar tests unitarios
pytest tests/

# Ejecutar ejemplo básico
python examples/basic_research.py

# Verificar imports
python -c "from agents.bibliomancer import BibliomancerAgent; print('OK')"
```

## 📊 Formato de Salida

### Documento Académico Generado

```
# Título del Documento

## Resumen
[Abstract estructurado]

## Introducción
[Contexto, problema, objetivos, justificación]

## Metodología
[Diseño, muestreo, análisis]

## Resultados
[Temas, clusters, evolución temporal]

## Discusión
[Consensos, contradicciones, limitaciones]

## Conclusiones
[Conclusiones, recomendaciones]

## Referencias
1. Autor, A. (2024). Título. Revista, Vol(Iss), pp-pp. https://doi.org/xxx
2. ...
```

### Visualizaciones Generadas

- `wordcloud_YYYYMMDD_HHMMSS.png` - Nube de palabras
- `bar_chart_YYYYMMDD_HHMMSS.png` - Frecuencia de términos
- `network_YYYYMMDD_HHMMSS.png` - Red semántica
- `timeline_YYYYMMDD_HHMMSS.png` - Evolución temporal
- `clusters_YYYYMMDD_HHMMSS.png` - Distribución de clusters
- `dashboard_YYYYMMDD_HHMMSS.png` - Dashboard resumen

## 🤝 Contribuir

1. Fork el proyecto
2. Crear rama feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit cambios (`git commit -am 'Add: nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abrir Pull Request

## 📄 Licencia

Este proyecto está bajo licencia MIT. Ver archivo `LICENSE` para detalles.

## 📞 Contacto

Para reportar bugs o solicitar funcionalidades, abrir un issue en el repositorio.

---

**KAI-Ethno** - Investigación Antropológica Aumentada con IA  
Parte del ecosistema [KognitoAI](https://github.com/tu-usuario/kognito-ai)
