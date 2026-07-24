# Changelog KAI-Ethno

Todos los cambios notables en este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/lang/es/).

## [1.0.0] - 2024-12-02

### Agregado
- Arquitectura multi-agente completa con 7 agentes especializados
- **KAI Core**: Orquestador central con LangGraph
- **Ethics Council**: Sistema de evaluación ética con 4 evaluadores y protocolo de veto
- **Bibliomancer**: Agente de recolección bibliográfica
- **Ethnograph**: Agente de procesamiento etnográfico
- **Synthesizer**: Agente de triangulación y síntesis
- **PatternFinder**: Agente de análisis de patrones
- **Archivist**: Agente de gestión de conocimiento
- **Visualizer**: Agente de visualizaciones
- **Scribe**: Agente de redacción académica
- Memoria distribuida con ChromaDB y Neo4j
- Message Bus asíncrono para comunicación entre agentes
- Sistema de estados Pydantic para validación de datos
- Script de instalación automatizado (`install.sh`)
- Documentación completa en README.md y SKILL.md
- Referencias académicas: bases de datos, marcos éticos, estilos de citación
- Ejemplos de uso: investigación básica y etnografía digital
- Estructura de directorios estándar para skills de KognitoAI
- Protocolo de veto ético con trazabilidad
- Detección de PII en materiales etnográficos
- Sistema de codificación (abierta, axial, selectiva)
- Análisis del discurso y Grounded Theory
- Generación de visualizaciones académicas
- Formateo automático de citas (APA 7th, Chicago 17th, MLA 9th, AAA)

### Características Técnicas
- Python 3.11+
- LangGraph para definición de flujos
- Pydantic para validación de estados
- AsyncIO para operaciones concurrentes
- Soporte para múltiples proveedores LLM (OpenAI, Anthropic, etc.)
- Integración con bases de datos académicas (PubMed, Scopus, Semantic Scholar)
- Almacenamiento vectorial para memoria semántica
- Grafo de conocimiento Neo4j para relaciones complejas

### Documentación
- README.md completo con arquitectura, instalación, uso y configuración
- SKILL.md con especificación de la skill para KognitoAI
- Referencias detalladas de bases de datos académicas
- Marcos éticos de referencia (GDPR, APA, AAA, Convenio de Oviedo)
- Guías de estilos de citación académica
- Ejemplos funcionales documentados

## [0.1.0] - 2024-11-15

### Agregado
- Estructura inicial de directorios
- Esqueletos base de agentes
- Configuración inicial del proyecto

---

## Formato de Versionado

- **MAJOR**: Cambios incompatibles en la API o arquitectura
- **MINOR**: Nuevas funcionalidades compatibles
- **PATCH**: Correcciones de bugs compatibles

## Tipos de Cambios

- `Agregado`: Nuevas funcionalidades
- `Modificado`: Cambios en funcionalidades existentes
- `Deprecado`: Funcionalidades que serán removidas
- `Removido`: Funcionalidades eliminadas
- `Corregido`: Corrección de bugs
- `Seguridad`: Vulnerabilidades corregidas
