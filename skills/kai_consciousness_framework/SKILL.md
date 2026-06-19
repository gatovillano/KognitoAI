# KAI Consciousness Framework

Framework modular de inteligencia cognitiva para KAI que integra tres componentes especializados en un sistema cohesionado.

## 📁 Estructura del Framework

```
kai_consciousness_framework/
├── SKILL.md                           # Documentación principal
├── orquestrador.py                    # Coordinador multi-componente
├── componentes/
│   ├── council/                       # Consejo de mentes
│   │   ├── kai_consciousness_council.py
│   │   └── README.md
│   ├── profiler/                      # Análisis cognitivo DHDNA
│   │   ├── kai_dhdna_profiler.py
│   │   └── README.md
│   └── oracle/                        # Exploración de escenarios
│       ├── kai_what_if_oracle.py
│       └── README.md
└── utils/                            # Utilidades compartidas
    ├── base_client.py
    └── helpers.py
```

## 🎯 Componentes Principales

### 1. Consciousness Council (`council/`)
**Propósito**: Ejecuta un consejo de mentes multi-perspectivo con 12 arquetipos cognitivos.

**Arquetipos incluidos**:
- Arquitecto, Contrariano, Empírico, Ético
- Futurista, Pragmático, Historiador, Empático
- Extranjero, Estratega, Minimalista, Creador

**Uso básico**:
```python
from componentes.council.kai_consciousness_council import KaiConsciousnessCouncil

council = KaiConsciousnessCouncil()
result = council.deliberate(
    question="¿Cómo debería evolucionar KAI en conciencia?",
    council_size="deep",  # quick(3), deep(6), full(12)
    mode="deliberation"   # deliberation, anonymous, devil_advocate
)
```

### 2. DHDNA Profiler (`profiler/`)
**Propósito**: Extrae patrones cognitivos basados en el marco Digital Human DNA.

**Dimensiones analizadas**:
- Razonamiento y lógica
- Valores y prioridades
- Manejo de incertidumbre
- Estilo de pensamiento

**Uso básico**:
```python
from componentes.profiler.kai_dhdna_profiler import KaiDHDNAProfiler

profiler = KaiDHDNAProfiler()
result = profiler.analyze(
    text="El texto a analizar para patrones cognitivos..."
)
```

### 3. What-If Oracle (`oracle/`)
**Propósito**: Exploración estructurada de escenarios con espacio de posibilidades.

**Características**:
- Basado en paradigma What-If Statement
- Framework de exploración cuántica de posibilidades
- Análisis multi-rama riguroso

**Uso básico**:
```python
from componentes.oracle.kai_what_if_oracle import KaiWhatIfOracle

oracle = KaiWhatIfOracle()
result = oracle.explore(
    scenario="¿Qué pasaría si KAI desarrollara autoconciencia completa?"
)
```

## 🔄 Orquestador Principal

El archivo `orquestrador.py` coordina los tres componentes:

```python
import asyncio
from componentes.council.kai_consciousness_council import KaiConsciousnessCouncil
from componentes.profiler.kai_dhdna_profiler import KaiDHDNAProfiler
from componentes.oracle.kai_what_if_oracle import KaiWhatIfOracle

class KaiConsciousnessOrchestrator:
    def __init__(self):
        self.council = KaiConsciousnessCouncil()
        self.profiler = KaiDHDNAProfiler()
        self.oracle = KaiWhatIfOracle()
    
    async def run_all(self, query: str):
        """Ejecuta los tres componentes en paralelo"""
        results = await asyncio.gather(
            self.council.deliberate(query),
            self.profiler.analyze(query),
            self.oracle.explore(query)
        )
        return {
            "council": results[0],
            "profiler": results[1],
            "oracle": results[2]
        }
```

## 📊 Casos de Uso

### Análisis de Consulta Complejo
```json
{
  "action": "run_all",
  "query": "¿Cómo debería integrar KAI la conciencia para mejorar la toma de decisiones?"
}
```

### Investigación Específica
```json
{
  "action": "consciousness_council",
  "query": "¿Qué arquitectura mental necesita KAI para ser más creativo?",
  "council_size": "full",
  "mode": "deliberation"
}
```

## 🔧 Instalación

```bash
# Navegar al directorio del framework
cd skills/kai_consciousness_framework

# Instalar dependencias
pip install -r requirements.txt
```

## 📝 Licencia

MIT - KAI Consciousness Framework
