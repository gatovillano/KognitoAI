---
name: skill-installer
description: |
  Procedimiento para interpretar solicitudes de instalación de skills, resolver
  enlaces o identificadores y decidir el flujo correcto de instalación.
license: MIT
compatibility: |
  Python 3.10+
  Compatible con el instalador interno de KognitoAI y con flujos tipo agentskills.io
metadata:
  author: KognitoAI Team
  version: "1.0.0"
  tags:
    - installation
    - skills
    - resolver
    - natural-language
  category: core
allowed-tools: |
  filesystem__read_file
  filesystem__write_file
  terminal__execute
---

# Skill Installer

## Cuándo usarla

Usa esta skill cuando el usuario quiera:

- Instalar una skill desde un enlace.
- Agregar una skill desde GitHub.
- Instalar desde skills.sh.
- Usar un comando tipo `npx skills add ...` o un identificador ambiguo.
- Pedir algo como “instala esta skill”, “agrega esta habilidad” o “usa este enlace”.

## Regla principal

Si el usuario pega un enlace o un identificador de skill, interprétalo primero como una solicitud de instalación, no como una simple referencia informativa.

## Orden de resolución

1. Ruta local válida dentro del workspace.
2. URL completa de GitHub.
3. Identificador `owner/repo`.
4. Identificador `owner/repo/subdir`.
5. URL o identificador de skills.sh.
6. Si sigue siendo ambiguo, pide solo el dato mínimo faltante.

## Procedimiento

1. Detecta la intención del usuario.
2. Normaliza la entrada.
3. Clasifica la fuente.
4. Resuelve el destino con el instalador.
5. Ejecuta la instalación.
6. Verifica el resultado.
7. Reporta qué se instaló y desde dónde.

## Casos comunes

### Caso 1: Ruta local

Ejemplo:

```text
./skills/mi_skill
```

Acción:
- Validar que exista `SKILL.md`.
- Instalar desde filesystem local.

### Caso 2: GitHub

Ejemplo:

```text
https://github.com/vercel-labs/skills
```

Acción:
- Normalizar a `owner/repo`.
- Resolver ramas o subdirectorios si existen.
- Instalar desde GitHub.

### Caso 3: skills.sh

Ejemplo:

```text
vercel-labs/skills/find-skills
```

Acción:
- Interpretar como entrada del registry.
- Delegar al resolver correspondiente.

### Caso 4: Ambiguo o incompleto

Ejemplo:

```text
instala esa skill
```

Acción:
- Pedir el enlace, ruta o identificador exacto.
- No inventar la fuente.

## Integración recomendada

- Usa `SkillInstaller.install_from_identifier()` para automatizar la resolución.
- Usa `SkillSourceResolver.normalize_identifier()` para limpiar URLs antes de resolver.
- Si el usuario solo te da un enlace, trátalo como una orden procedimental.

## Resultado esperado

Al aplicar esta skill, el agente debe poder decir:

- “Entendí que quieres instalar esta skill desde GitHub.”
- “Voy a normalizar el enlace y resolver la fuente.”
- “La instalación quedó lista y ya fue registrada.”