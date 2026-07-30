---
name: core-skills
description: Use when accessing core system capabilities, managing registered skills,
  or editing skill definitions.
---

name: onboarding-experto
description: |
  Procedimiento experto para onboarding de un nuevo usuario en KAI OS, combinando varias herramientas y skills.
---

## Objetivo
Guiar al usuario paso a paso para configurar su cuenta, importar datos, personalizar preferencias y entender las funciones clave del sistema.

## Procedimiento detallado
1. **Verificar identidad:**
    - Usar la skill de autenticación para validar correo y teléfono.
    - Si falla, pedir reintento o soporte.
2. **Importar datos previos:**
    - Preguntar si el usuario tiene datos de otro sistema.
    - Si sí, usar la skill de importación de datos.
    - Si no, saltar al paso 3.
3. **Configurar preferencias:**
    - Guiar al usuario para elegir idioma, zona horaria y notificaciones.
    - Usar la skill de configuración de usuario.
4. **Explicar funciones clave:**
    - Mostrar un resumen de las skills principales disponibles.
    - Recomendar skills según el perfil detectado.
5. **Validar onboarding:**
    - Confirmar que el usuario puede acceder a su dashboard y realizar una acción básica.

## Reglas y advertencias
- Si el usuario se bloquea en cualquier paso, ofrecer ayuda contextual.
- Documentar cada decisión y resultado en el log de onboarding.
- No avanzar al siguiente paso hasta que el anterior esté confirmado.

## Ejemplo de integración
El agente debe seguir este procedimiento al pie de la letra, invocando las skills y herramientas necesarias en cada paso, y reportando el avance al usuario.
```

---

# Skill Factory (KAI OS Application Builder)

La Skill Factory es el generador oficial de "aplicaciones" para KAI, que funciona como un sistema operativo cognitivo. Cada skill es un programa autocontenible, instalable y orquestable, que puede componerse de múltiples scripts, módulos y lógica de integración. Todas las skills deben tener su documentación principal en un archivo llamado **SKILL.md**.

---

## Visión: Skills como Aplicaciones de KAI OS

Imagina a KAI como un sistema operativo donde cada skill es una aplicación: puede ser simple (una sola función) o compleja (un conjunto de scripts, orquestadores, dependencias internas, integración con APIs, UI, etc). Las skills pueden interactuar entre sí, ser orquestadas, y evolucionar como verdaderos programas.

---

## Formato y Estructura Rigurosa

**Directorio estándar de una skill:**

```
skills/
    <scope>/
        <nombre_skill>_skill/
            SKILL.md                # Documentación y especificación principal (obligatorio)
            scripts/
                main.py               # Script principal (puede haber varios)
                modulo_extra.py       # Scripts auxiliares
                orquestador.py        # (Opcional) Orquestador de lógica multi-script
            __init__.py
```

**Reglas:**
- El archivo de especificación y ayuda siempre se llama `SKILL.md` (no otro nombre).
- **Formato OBLIGATORIO de SKILL.md:** Debe comenzar con YAML frontmatter delimitado por `---`:
  ```yaml
  ---
  name: nombre-de-la-skill
  description: Descripción clara y detallada de cuándo y cómo el agente debe usar esta habilidad.
  ---
  ```
- Puede haber múltiples scripts Python en la carpeta `scripts/`.
- Si la skill es compleja, debe incluir un orquestador (ej: `orquestador.py`) que coordine los módulos internos.
- El orquestador debe exponer una clase principal que herede de `BaseTool` y reciba como dependencias los sub-módulos.
- La documentación en SKILL.md debe ser procedimental, exhaustiva y contener:
    - YAML Frontmatter (`name` y `description`)
    - Cuándo usar la skill
    - Ejemplos de uso
    - Descripción de cada script y su función
    - Diagrama de flujo/orquestación (si aplica)
    - Parámetros y outputs esperados
    - Reglas de integración con otras skills
    - Casos de borde y advertencias
    - Ejemplo de instalación y actualización

---

## Procedimiento para crear una skill robusta (aplicación)

1. **Define el objetivo**: ¿Qué problema resuelve la skill? ¿Es una app simple o compuesta?
2. **Diseña la arquitectura**: Divide la lógica en scripts autocontenibles. Si es necesario, crea un orquestador que los coordine.
3. **Implementa los scripts**: Cada script debe tener una función clara y documentada. Usa clases y tipado estricto.
4. **Crea el orquestador**: Implementa una clase principal que herede de `BaseTool`, reciba los sub-módulos y exponga la interfaz pública.
5. **Documenta en SKILL.md**: Explica el flujo, los módulos, los parámetros, los outputs, los casos de uso y las advertencias.
6. **Ejecuta la Skill Factory**: Pasa el nombre, los scripts y el SKILL.md. (En versiones futuras, la Skill Factory aceptará múltiples scripts y orquestadores).
7. **Verifica la instalación**: La skill debe estar disponible como una aplicación autocontenida en KAI OS.

---

## Ejemplo de skill multi-script y orquestada

```
skills/
    user_account_XXXX/
        weather_dashboard_skill/
            SKILL.md
            scripts/
                fetch_weather.py      # Obtiene datos de la API
                process_data.py       # Procesa y normaliza los datos
                render_dashboard.py   # Genera el dashboard visual
                orquestador.py        # Coordina todo el flujo
            __init__.py
```

**orquestador.py:**
```python
from langchain_core.tools import BaseTool
from .fetch_weather import WeatherFetcher
from .process_data import WeatherProcessor
from .render_dashboard import DashboardRenderer

class WeatherDashboardOrchestrator(BaseTool):
        name = "weather_dashboard"
        description = "Orquesta la obtención, procesamiento y visualización del clima."

        def _run(self, location: str) -> str:
                raw = WeatherFetcher().fetch(location)
                processed = WeatherProcessor().process(raw)
                dashboard = DashboardRenderer().render(processed)
                return dashboard
```

**SKILL.md (extracto):**
```
---
name: weather_dashboard
description: |
    Aplicación compuesta que obtiene el clima, procesa los datos y genera un dashboard visual.
    Usa 3 scripts internos y un orquestador.
---

## Cuándo usar
- Cuando el usuario pide un resumen visual del clima.

## Flujo de orquestación
1. `fetch_weather.py` obtiene los datos de la API.
2. `process_data.py` normaliza y filtra los datos.
3. `render_dashboard.py` genera el dashboard.
4. `orquestador.py` coordina todo el flujo.

## Ejemplo de uso
```python
orquestador = WeatherDashboardOrchestrator()
result = orquestador._run(location="Santiago, CL")
```
```

---

## Recomendaciones y advertencias
- Documenta exhaustivamente cada módulo.
- Usa tipado estricto y validación de parámetros.
- Si la skill depende de otras skills, documenta la integración.
- Mantén el SKILL.md actualizado con cada cambio.

---

## Resumen

La Skill Factory es el mecanismo oficial para crear aplicaciones (skills) en KAI OS. Toda skill debe tener su SKILL.md, puede componerse de múltiples scripts y debe ser orquestable. Piensa en cada skill como un programa autocontenible, instalable y actualizable dentro del ecosistema KAI.

---
