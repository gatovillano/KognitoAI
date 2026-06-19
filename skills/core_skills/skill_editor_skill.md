# Skill Editor Skill

Esta habilidad permite al agente de KAI modificar, actualizar y corregir el código de otras habilidades (Skills) instaladas en el sistema.

## Capacidades
- **Sobrescribir Scripts**: Actualiza el archivo `.py` principal de cualquier skill.
- **Actualizar Documentación**: Modifica las instrucciones `.md` de una skill.
- **Reparación Dinámica**: Corregir errores en caliente (HOTFIX) de habilidades existentes.

## Uso Técnico
`skill_editor(skill_name: str, scope: str, new_python_code: Optional[str] = None, new_markdown_description: Optional[str] = None)`

> [!IMPORTANT]
> El campo `skill_name` debe ser el nombre del directorio (ej: `host_terminal_skill`) y el `scope` debe indicar dónde buscar (ej: `user_account_5b8d59b0-69b7-4aa8-9bb0-bf07511222a6`).
