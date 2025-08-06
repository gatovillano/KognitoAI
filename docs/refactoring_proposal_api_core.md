# Propuesta de Refactorización: API, Core y Utils

## Resumen Ejecutivo

Tras un análisis de la estructura del código en los directorios `api/`, `core/` y `utils/`, se ha identificado una oportunidad significativa para refactorizar el código. El objetivo es mejorar la mantenibilidad, reducir la duplicación de código y fortalecer la Separación de Responsabilidades (SoC) entre la capa de API y la lógica de negocio principal.

## Análisis de Áreas de Refactorización

### 1. Duplicación de la Gestión de Sesiones de Base de Datos

*   **Observación:** Casi todos los archivos en `api/` (como `agenda.py`, `analysis.py`, `auth.py`, `documents.py`, `teams.py`, etc.) definen su propia función `get_db()` para gestionar las sesiones de `AsyncSession`.
*   **Problema:** Esto representa una duplicación de código de manual. Si la forma de obtener una sesión de base de datos cambia, habría que actualizarla en más de 10 lugares distintos.
*   **Solución Existente:** El proyecto ya cuenta con una solución elegante para esto en `utils/db_session.py` con el gestor de contexto `DBSession`. Sin embargo, no se está utilizando consistentemente en los endpoints de la API.

### 2. Lógica de Negocio Directamente en la Capa de API

*   **Observación:** Varios endpoints en el directorio `api/` contienen lógica de negocio compleja que va más allá de la simple gestión de la petición HTTP.
    *   **`api/analysis.py`:** Contiene las funciones completas para ejecutar análisis en segundo plano (`run_document_analysis_and_save`, `run_collection_analysis_and_save`, `run_semantic_topic_analysis`). Estas funciones son el "corazón" del análisis y deberían residir en `core/`.
    *   **`api/teams.py`:** Los endpoints para crear, listar, y gestionar miembros de equipos realizan consultas directas a la base de datos. Esta lógica pertenece a un "manager" o "servicio" en `core/`.
    *   **`api/documents.py`:** La función `process_upload_task` que maneja la subida y procesamiento de documentos en segundo plano está definida aquí, pero es lógica de `core`.
*   **Problema:** Mezclar la lógica de negocio con la capa de API (FastAPI) hace que el código sea más difícil de probar, mantener y reutilizar. La capa de API debería ser lo más "delgada" posible, delegando el trabajo pesado a la capa `core`.

### 3. Duplicación de Funcionalidad en `utils/`

*   **Observación:** Existen dos archivos con una funcionalidad casi idéntica: `utils/document_analysis.py` y `utils/collection_analysis.py`. Ambos contienen una función `extract_concepts_from_document`. Además, el archivo `utils/advanced_text_analyzer.py` parece ser una versión más robusta y estructurada de estas mismas ideas.
*   **Problema:** Múltiples implementaciones de la misma lógica conducen a inconsistencias y a un mayor esfuerzo de mantenimiento.

## Plan de Refactorización Propuesto

Para abordar estos puntos, se propone el siguiente plan de acción:

1.  **Centralizar la Gestión de Sesiones de DB:**
    *   Eliminar todas las funciones `get_db()` duplicadas de los archivos en `api/`.
    *   Refactorizar todos los endpoints que usan `Depends(get_db)` para que utilicen el gestor de contexto `async with DBSession(SessionLocal) as db:` para interactuar con la base de datos.

2.  **Crear y Mover a "Managers" en la Capa `core`:**
    *   Crear un nuevo archivo `core/analysis_manager.py` y mover toda la lógica de las funciones de análisis en segundo plano desde `api/analysis.py`.
    *   Crear un nuevo archivo `core/teams_manager.py` y mover toda la lógica de gestión de equipos desde `api/teams.py`.
    *   Hacer lo mismo para otros módulos de la API que contengan lógica de negocio sustancial.

3.  **Consolidar Utilidades de Análisis de Texto:**
    *   Eliminar los archivos `utils/document_analysis.py` y `utils/collection_analysis.py`.
    *   Modificar el código que los usaba para que en su lugar llamen a los métodos más robustos de la clase `AdvancedTextAnalyzer` en `utils/advanced_text_analyzer.py`.

4.  **Adelgazar los Endpoints de la API:**
    *   Una vez que la lógica de negocio se haya movido a los managers en `core/`, los endpoints en `api/` se volverán muy simples. Su única responsabilidad será recibir la petición, llamar al manager correspondiente y devolver la respuesta.

Este plan de refactorización resultará en un código base mucho más limpio, organizado, fácil de mantener y de probar.
