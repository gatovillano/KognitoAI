# Propuesta de Refactorización: API y Core

Este documento describe una propuesta técnica para refactorizar la aplicación, con el objetivo de separar la lógica de negocio de la capa de API. El objetivo es migrar toda la lógica de negocio de los módulos en `/api` a sus contrapartes en `/core`, dejando los endpoints de la API con la única responsabilidad de manejar el protocolo HTTP.

## Principios de Diseño a Seguir

1.  **Principio de Responsabilidad Única (SRP):**
    *   **Módulos en `/api`:** Su única responsabilidad es:
        *   Recibir peticiones HTTP.
        *   Validar los datos de entrada (usando Pydantic).
        *   Llamar al método correspondiente en el "manager" de `/core`.
        *   Manejar excepciones específicas de la lógica de negocio y traducirlas a códigos de estado HTTP apropiados (ej. 404, 400, 500).
        *   Formatear y devolver la respuesta.
    *   **Módulos en `/core`:** Su responsabilidad es:
        *   Contener toda la lógica de negocio (crear, leer, actualizar, eliminar datos).
        *   Interactuar con la base de datos, cachés, y otros servicios.
        *   No tener conocimiento del protocolo HTTP. No deben manejar `Request` o `Response` de FastAPI.

2.  **Inyección de Dependencias (Dependency Injection):**
    *   Para desacoplar completamente la capa de API de la capa de negocio, usaremos el sistema de inyección de dependencias de FastAPI (`Depends`).
    *   Los endpoints en `/api` no crearán instancias de los "managers" de `/core`. En su lugar, los recibirán como dependencias. Esto facilita enormemente las pruebas unitarias.

3.  **Flujo de Datos Claro:**
    *   Los datos fluirán en una dirección: `API Endpoint -> Core Manager -> Base de Datos` y viceversa. Se deben usar modelos de Pydantic para definir los contratos de datos entre estas capas.

---

## Plan Técnico Detallado

Realizaremos esta refactorización de forma incremental, módulo por módulo, para minimizar el riesgo.

### Fase 1: Análisis e Identificación (Ejemplo: `api/notes.py`)

1.  **Identificar Lógica de Negocio:** Analizar el contenido de los archivos en `/api` para identificar cualquier código que no esté directamente relacionado con la gestión de la petición HTTP. Esto incluye:
    *   Consultas directas a la base de datos.
    *   Lógica de procesamiento de datos.
    *   Llamadas a otros servicios o herramientas.

2.  **Definir la Interfaz en el Manager de `/core`:** Basado en la lógica identificada, se definirán los métodos necesarios en el "manager" correspondiente (ej. `core/notes_manager.py`).

### Fase 2: Refactorización (Ejemplo Práctico)

**Estado Actual Hipotético en `api/notes.py`:**

```python
@router.post("/notes/", response_model=Note)
def create_note(note: NoteCreate, db: Session = Depends(get_db)):
    # --- INICIO DE LÓGICA DE NEGOCIO (A MOVER) ---
    if not note.title or not note.content:
        raise HTTPException(status_code=400, detail="Title and content are required.")
    
    db_note = NoteModel(title=note.title, content=note.content, owner_id=1)
    db.add(db_note)
    db.commit()
    db.refresh(db_note)
    # --- FIN DE LÓGICA DE NEGOCIO ---
    return db_note
```

**Paso 1: Mover la lógica a `core/notes_manager.py`**

```python
class NotesManager:
    def __init__(self, db: Session):
        self.db = db

    def create_note(self, note_data: NoteCreate, owner_id: int) -> NoteModel:
        if not note_data.title or not note_data.content:
            # Lanzar una excepción de negocio, no HTTP
            raise ValueError("Title and content are required.")
        
        db_note = NoteModel(**note_data.dict(), owner_id=owner_id)
        self.db.add(db_note)
        self.db.commit()
        self.db.refresh(db_note)
        return db_note
```

**Paso 2: Limpiar el endpoint en `api/notes.py`**

```python
# Helper para la inyección de dependencias
def get_notes_manager(db: Session = Depends(get_db)) -> NotesManager:
    return NotesManager(db)

@router.post("/notes/", response_model=Note)
def create_note(
    note: NoteCreate,
    notes_manager: NotesManager = Depends(get_notes_manager)
):
    try:
        # La única responsabilidad es llamar al manager y manejar errores
        current_user_id = 1 # Este ID vendría del sistema de autenticación
        new_note = notes_manager.create_note(note_data=note, owner_id=current_user_id)
        return new_note
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Manejo de errores inesperados
        raise HTTPException(status_code=500, detail="An internal error occurred.")
```

### Fase 3: Aplicación Gradual

Se recomienda repetir este proceso para cada par de archivos (`api/users.py` -> `core/user_manager.py`, `api/documents.py` -> `core/document_manager.py`, etc.) para asegurar una transición controlada y estable.
