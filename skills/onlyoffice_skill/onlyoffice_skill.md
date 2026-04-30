# ONLYOFFICE_SKILL: Gestión Proactiva de Documentos y Hoja de Cálculo

Esta habilidad permite al agente interactuar directamente con los documentos almacenados en el módulo OnlyOffice del usuario. A diferencia de la Base de Conocimientos (RAG), que busca fragmentos, esta habilidad permite leer el **contenido íntegro y exacto** de archivos de oficina.

## Cuándo usar esta habilidad:
- El usuario pide "leer", "resumir", "analizar" o "editar mentalmente" un archivo específico por su nombre.
- El usuario quiere saber qué archivos tiene en un Workspace específico de OnlyOffice.
- El usuario pregunta por datos específicos dentro de una hoja de cálculo (Excel) o un documento Word (.docx).
- Cuando el usuario menciona un archivo que ha "subido" o "creado" en OnlyOffice.

## Herramientas principales:
1. `search_onlyoffice_documents_tool`: Úsala para listar archivos en una carpeta o workspace, o para encontrar un archivo por su nombre aproximado.
2. `read_onlyoffice_document_tool`: Úsala para obtener TODO el texto legible de un archivo (.docx, .xlsx, .txt, .csv, .pptx).

## Flujo de trabajo RECOMENDADO:
1. Si el usuario pide leer un archivo pero no estás seguro del nombre exacto, primero usa `search_onlyoffice_documents_tool` para confirmar su existencia.
2. Una vez tengas el ID o el nombre exacto, usa `read_onlyoffice_document_tool` para procesar el contenido.
3. Si el archivo es una hoja de cálculo, avisa al usuario que estás leyendo las celdas directamente.

## Limitaciones:
- No puedes leer archivos PDF (para eso usa la skill de RAG o Document Management estándar).
- No puedes leer archivos de imagen (.png, .jpg) a menos que uses herramientas de visión.
- El tamaño del archivo puede ser grande; el agente truncará la salida si excede los límites de contexto del LLM.

---
**IMPORTANTE**: Siempre respeta el `workspace_id` activo para buscar documentos dentro del contexto correcto del proyecto del usuario.
