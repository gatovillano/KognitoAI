# Guía de Refactorización: Skills según agentskills.io

## 🎯 Objetivo
Refactorizar las skills de KognitoAI para seguir el estándar abierto **agentskills.io**, mejorando:
- **Discovery**: Agentes pueden encontrar skills de forma consistente
- **Composability**: Skills pueden componerse entre sí
- **Portability**: Skills reutilizables en otros agentes
- **Compatibility**: Compatible con Claude Code, agent-codemode, Pydantic AI, etc.

## 📋 Estructura Esperada (agentskills.io Standard)

```
skills/
├── my-skill/                    # nombre-en-minusculas-con-guiones
│   ├── SKILL.md                 # ← REQUERIDO: metadata + instrucciones
│   ├── scripts/
│   │   ├── main_function.py    # Python ejecutable
│   │   └── helper.py
│   ├── references/              # Documentación adicional (opcional)
│   │   ├── REFERENCE.md
│   │   ├── examples.md
│   │   └── troubleshooting.md
│   ├── assets/                  # Recursos estáticos (opcional)
│   │   ├── templates/
│   │   ├── data/
│   │   └── images/
│   └── README.md                # Documentación para devs (opcional)
```

## 📝 Formato SKILL.md Requerido

### Estructura Básica
```yaml
---
name: skill-name              # lowercase-with-hyphens, debe coincidir con directorio padre
description: |               # Descripción clara: qué hace y cuándo usarla (max 1024 chars)
  Descripción de lo que hace este skill.
  Incluye casos de uso específicos.
license: MIT                  # Opcional: Apache-2.0, MIT, Proprietary, etc.
compatibility: |              # Opcional: requisitos de entorno
  Requires Python 3.10+
  Requires database access
metadata:                     # Opcional: metadatos adicionales
  author: KognitoAI Team
  version: "1.0.0"
  tags:
    - search
    - web
  category: research
allowed-tools: |              # Opcional: tools aprobadas (experimental)
  filesystem__read_file
  network__fetch
---

# Skill Name (h1)

## Descripción
Explicación detallada de qué hace este skill.

## Cuándo Usarlo
- Caso de uso 1: ...
- Caso de uso 2: ...

## Cómo Usarlo
Instrucciones paso a paso para usar el skill.

### Parámetros
- `param1` (str): Descripción
- `param2` (int): Descripción

### Ejemplos
```python
# Ejemplo 1
result = await my_skill(param1="value")
```

## Referencias
Ver [REFERENCE.md](references/REFERENCE.md) para detalles técnicos.

## Solución de Problemas
Ver [troubleshooting.md](references/troubleshooting.md).
```

## 🔄 Proceso de Migración de Skills Existentes

### Paso 1: Crear SKILL.md
1. Renombra `skill_name.md` → archivo de referencia (si es relevante)
2. Crea nuevo `SKILL.md` con YAML frontmatter
3. Adapta contenido existente a las nuevas secciones

### Paso 2: Estructura de Directorios
```bash
# Antes
skills/
└── search_and_research_skill/
    ├── search_and_research_skill.md
    ├── tavily_search_tool.md
    ├── scripts/
    │   ├── tavily_search_tool.py
    │   └── ...
    └── __init__.py

# Después
skills/
└── search-and-research/
    ├── SKILL.md                     # ← Nuevo: YAML + instrucciones principales
    ├── scripts/
    │   ├── tavily_search.py
    │   └── web_scraper.py
    ├── references/
    │   ├── REFERENCE.md              # ← Detalles técnicos complejos
    │   ├── api-integrations.md
    │   └── examples.md
    ├── assets/
    │   └── search-patterns.json
    └── README.md                    # ← Para desarrolladores
```

### Paso 3: Validación
```bash
# Validar SKILL.md contra especificación
npx @agentskills/cli validate skills/search-and-research/

# O using skills-ref (Go)
skills-ref validate ./skills/search-and-research/
```

## 📊 Tabla de Migración

| Skill Actual | Nuevo Nombre | Prioridad | Estado |
|---|---|---|---|
| search_and_research_skill | search-and-research | P0 | Pendiente |
| rag_skill | retrieval-augmented-generation | P0 | Pendiente |
| knowledge_and_memory_skill | knowledge-memory-management | P0 | Pendiente |
| document_management_skill | document-management | P1 | Pendiente |
| core_skills | core-fundamentals | P1 | Pendiente |
| media_and_generation_skill | media-generation | P1 | Pendiente |
| notes_skill | notes-management | P2 | Pendiente |
| calendar_skill | calendar-management | P2 | Pendiente |
| email_checker_skill | email-checking | P2 | Pendiente |

## 🛠️ Comandos Útiles

### Crear nueva estructura
```bash
mkdir -p skills/skill-name/{scripts,references,assets}
touch skills/skill-name/SKILL.md
touch skills/skill-name/README.md
```

### Validar frontmatter YAML
```bash
# Python
pip install pyyaml
python scripts/validate_skills.py

# Node.js
npm install -g agent-skills-cli
agent-skills validate ./skills
```

## 📚 Características Avanzadas (Fase 2)

### Progressive Disclosure
- Metadata (~100 tokens): cargado al startup
- Instructions (~5000 tokens): cargado cuando se activa
- Resources (on-demand): cargado cuando se necesita

### Composición de Skills
```markdown
## Composición con Otros Skills

Este skill puede combinarse con:
- [search-and-research](../search-and-research) para mejorar búsquedas
- [document-management](../document-management) para gestionar resultados
```

### Tool Access Policies
```yaml
allowed-tools: |
  filesystem__read_file
  filesystem__write_file
  
denied-tools: |
  network__external_api
```

## 🔗 Referencias

- [agentskills.io Specification](https://agentskills.io/specification)
- [Agent Skills PyPI](https://pypi.org/project/agent-skills/)
- [Datalayer Agent Skills Docs](https://agent-skills.datalayer.tech/)
- [Claude Code Skills Integration](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)

## ✅ Checklist para Cada Skill

- [ ] `SKILL.md` creado con YAML frontmatter válido
- [ ] Nombre sigue convención: lowercase-with-hyphens
- [ ] Descripción clara: qué hace + cuándo usarlo (< 1024 chars)
- [ ] Instrucciones en Markdown (sin restricciones de formato)
- [ ] Scripts en `scripts/` carpeta
- [ ] Referencias técnicas en `references/` (si aplica)
- [ ] README.md para desarrolladores (opcional pero recomendado)
- [ ] Validado contra especificación
- [ ] Testeable y ejecutable independientemente
