# 🚀 Plan de Implementación: Refactorización Skills a agentskills.io

## 📊 Estado Actual

```
Total Skills: 17
├─ ✅ Listos (3): knowledge, rag, search
├─ ⚠️ Warnings (3): nombres no coinciden con directorios
└─ ❌ Faltantes (14): sin SKILL.md

Validator: ✅ Activo (scripts/validate_skills.py)
Template: ✅ Disponible (skills/_templates/template-skill/)
Guía: ✅ Completa (REFACTOR_SKILLS_GUIDE.md)
```

## 🎯 Objetivo de Migración

Migrar **100% de skills** a formato agentskills.io compatible con:
- ✅ Claude Code (Anthropic)
- ✅ agent-codemode (Datalayer)
- ✅ Pydantic AI
- ✅ agent-skills (agentskills.io)

## 📋 Fase 1: Fixing (1-2 horas)

### Paso 1.1: Corregir Nombres de 3 Skills Existentes
**Opción A: Renombrar Directorios (RECOMENDADO)**
```bash
# Antes (snake_case)
skills/knowledge_and_memory_skill/      → skills/knowledge-memory-management/
skills/rag_skill/                        → skills/retrieval-augmented-generation/
skills/search_and_research_skill/        → skills/search-and-research/

# Actualizar imports en el código:
# core/agent.py, core/skill_manager.py, etc.
```

**Pros:**
- Cumple 100% con especificación
- Nombres consistentes y claros
- Mejor portabilidad

**Contras:**
- Requiere actualizar imports en codebase

**Opción B: Mantener Directorios (RÁPIDO)**
- Cambiar `name:` en SKILL.md para coincidir con directorio
- Cumplimiento parcial de spec (mejor que nada)
- Sin cambios de imports

### Paso 1.2: Crear SKILL.md para 14 Skills Faltantes

**Prioridad P0 (investigación/análisis):**
```
- analysis-and-insights (→ analysis_and_insights_skill)
- document-management (→ document_management_skill)  
- data-and-forms (→ data_and_forms_skill)
```

**Prioridad P1 (gestión):**
```
- notes-management (→ notes_skill)
- profile-and-tasks (→ profile_and_tasks_skill)
- calendar-management (→ calendar_skill)
```

**Prioridad P2 (utilidades):**
```
- core-fundamentals (→ core_skills)
- media-generation (→ media_and_generation_skill)
- email-checking (→ email_checker_skill)
- developer-tools (→ developer_tools_skill)
- onlyoffice-integration (→ onlyoffice_skill)
```

**Prioridad P3 (personalizadas):**
```
- user-account-* (→ user_account_*/SKILL.md)
- user-global (→ user_global/SKILL.md)
```

### Paso 1.3: Validar
```bash
python3 scripts/validate_skills.py --skills-dir skills
# Resultado esperado: 17/17 ✅
```

## 📝 Fase 2: Enhancements (2-4 horas)

### Paso 2.1: Crear Estructura Completa

Para skills **complejos** (P0 + P1), crear:

```
skill-name/
├── SKILL.md                 # ✅ Ya existe
├── scripts/                 # ✅ Ya existe
├── references/              # 🆕 Crear
│   ├── REFERENCE.md         # Detalles técnicos
│   ├── api-reference.md     # Si aplica
│   ├── examples.md          # Casos avanzados
│   └── troubleshooting.md   # Problemas comunes
├── assets/                  # 🆕 Si aplica
│   ├── templates/
│   ├── examples/
│   └── data/
└── README.md                # 🆕 Para devs
```

### Paso 2.2: Documentación de Composición

Actualizar SKILL.md de cada skill con:
```markdown
## Composición con Otros Skills

Este skill trabaja bien con:
- [search-and-research](../search-and-research) - para obtener datos
- [knowledge-memory-management](../knowledge-memory-management) - para guardar
- [analysis-and-insights](../analysis-and-insights) - para analizar
```

### Paso 2.3: Test & Discovery

```bash
# Crear test de discovery
pytest tests/test_skill_discovery.py -v

# Simular carga de skills por agente
python3 scripts/test_skill_loading.py
```

## 🔧 Fase 3: Integration (1-2 horas)

### Paso 3.1: Actualizar Skill Manager

```python
# core/skill_manager.py
class SkillManager:
    def discover_skills(self) -> List[SkillMetadata]:
        """Descubre skills siguiendo agentskills.io spec"""
        skills = []
        for skill_dir in self.skills_path.glob("*"):
            skill_md = skill_dir / "SKILL.md"
            if skill_md.exists():
                metadata = self._parse_skill_md(skill_md)
                skills.append(metadata)
        return skills
    
    def _parse_skill_md(self, skill_md: Path) -> SkillMetadata:
        """Parsea frontmatter YAML + markdown"""
        with open(skill_md) as f:
            content = f.read()
        
        # Split frontmatter
        parts = content.split("---", 2)
        frontmatter = yaml.safe_load(parts[1])
        body = parts[2]
        
        return SkillMetadata(
            name=frontmatter["name"],
            description=frontmatter["description"],
            license=frontmatter.get("license"),
            compatibility=frontmatter.get("compatibility"),
            body=body,
            scripts=self._find_scripts(skill_dir)
        )
```

### Paso 3.2: Agente Integration

```python
# Actualizar core/agent.py
from core.skill_manager import SkillManager

class Agent:
    def __init__(self, ...):
        self.skills = SkillManager(settings.SKILLS_PATH)
    
    async def select_skill(self, task: str) -> SkillMetadata:
        """Progressive disclosure: load name+description, activate full SKILL.md"""
        # 1. Discovery: búsqueda por metadata
        candidates = self.skills.search(task)
        
        # 2. Activation: cargar instrucciones completas
        if candidates:
            return self.skills.load_skill(candidates[0].name)
        
        return None
```

### Paso 3.3: CLI & Server Updates

```python
# Crear CLI para explorar skills
@click.command()
@click.argument("action", type=click.Choice(["list", "show", "validate"]))
@click.option("--skill", help="Nombre del skill")
def cli_skills(action, skill):
    manager = SkillManager("./skills")
    
    if action == "list":
        for s in manager.discover_skills():
            click.echo(f"{s.name}: {s.description}")
    
    elif action == "show" and skill:
        s = manager.load_skill(skill)
        click.echo(s.body)
    
    elif action == "validate":
        # Ejecutar validator
        from scripts.validate_skills import SkillValidator
        validator = SkillValidator()
        validator.validate_all()
```

## 🗂️ Tabla de Acciones Concretas

| Skill | Acción | Prioridad | Est. Tiempo |
|---|---|---|---|
| knowledge_and_memory_skill | Renombrar + SKILL.md ✅ | P0 | 15min |
| rag_skill | Renombrar + SKILL.md ✅ | P0 | 15min |
| search_and_research_skill | Renombrar + SKILL.md ✅ | P0 | 15min |
| document_management_skill | Crear SKILL.md | P0 | 30min |
| data_and_forms_skill | Crear SKILL.md | P0 | 30min |
| analysis_and_insights_skill | Crear SKILL.md | P0 | 30min |
| notes_skill | Crear SKILL.md | P1 | 20min |
| profile_and_tasks_skill | Crear SKILL.md | P1 | 20min |
| calendar_skill | Crear SKILL.md | P1 | 20min |
| core_skills | Crear SKILL.md | P2 | 15min |
| media_and_generation_skill | Crear SKILL.md | P2 | 20min |
| email_checker_skill | Crear SKILL.md | P2 | 15min |
| developer_tools_skill | Crear SKILL.md | P2 | 15min |
| onlyoffice_skill | Crear SKILL.md | P2 | 15min |
| user_account_* (2) | Crear SKILL.md | P3 | 20min |
| user_global | Crear SKILL.md | P3 | 10min |
| **Total** | | | **~4-5 horas** |

## ✅ Checklist de Completitud

### Fase 1: Fixing
- [ ] Decisión: renombrar directorios o mantener
- [ ] 3 skills ✅ + 14 SKILL.md pendientes
- [ ] Validator pass 17/17
- [ ] Actualizar imports en código (si aplica)

### Fase 2: Enhancements
- [ ] Crear references/ para skills P0+P1
- [ ] Actualizar composición en SKILL.md
- [ ] Test discovery funcionando
- [ ] README.md para cada skill

### Fase 3: Integration
- [ ] SkillManager actualizado
- [ ] Agent usando agentskills.io format
- [ ] CLI funcionando
- [ ] Tests de integración pasando
- [ ] Documentación actualizada

## 🔗 Referencias

- [agentskills.io Specification](https://agentskills.io/specification)
- [Guía de Refactorización](./REFACTOR_SKILLS_GUIDE.md)
- [Validador de Skills](./scripts/validate_skills.py)
- [Template de Skill](./skills/_templates/template-skill/SKILL.md)

## 📞 Próximos Pasos

**Opción 1: Automático (Recomendado)**
```bash
# Script que crea todos los SKILL.md faltantes
python3 scripts/generate_missing_skills.py

# Valida resultado
python3 scripts/validate_skills.py
```

**Opción 2: Manual (Gradual)**
- Crear SKILL.md uno por uno
- Ir validando con validator
- Revisar y mejorar progresivamente

**¿Qué prefieres hacer primero?**

1. ✅ **Crear automáticamente los 14 SKILL.md faltantes** (usando templates inteligentes)
2. 🔄 **Renombrar directorios** a convención kebab-case
3. 📚 **Mejorar documentación** con references/ y assets/
4. 🧪 **Crear tests** de discovery e integración
