# Cambios

## 2025-05-20
- Corregido `core/skill_manager.py`: `parse_skill_markdown` ya no asume que el frontmatter YAML parseado es un diccionario. Ahora valida el tipo de `frontmatter` tras `yaml.safe_load` y, si es un u otros valores escalares, lo normaliza a `{}` antes de llamar a `.get(...)`. Esto evita el `AttributeError` al cargar skills con frontmatter no estructurado o texto plano delimitado por `---`.
