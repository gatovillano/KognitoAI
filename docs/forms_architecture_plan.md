# Arquitectura de Componentes para la Funcionalidad de Formularios

Este documento detalla la arquitectura de componentes de React para la nueva funcionalidad de "Formularios".

## Estructura de Directorios

```
src/
|-- app/
|   |-- (dashboard)/
|   |   |-- forms/
|   |   |   |-- page.tsx                   # Página principal de formularios (/forms)
|   |   |   |-- new/
|   |   |   |   |-- page.tsx               # Página de creación de formulario (/forms/new)
|   |   |   |-- [formId]/
|   |   |   |   |-- page.tsx               # Página de visualización de formulario (/forms/[formId])
|   |   |   |   |-- edit/
|   |   |   |   |   |-- page.tsx           # Página de edición de formulario (/forms/[formId]/edit)
|   |   |-- fill/
|   |   |   |-- [formId]/
|   |   |   |   |-- page.tsx               # Página pública para rellenar formulario (/forms/fill/[formId])
|-- components/
|   |-- forms/
|   |   |-- FormCard.tsx
|   |   |-- FormField.tsx
|   |   |-- ResponseCard.tsx
```

## Diseño de Componentes

### 1. `FormsPage` (`/forms`)

*   **Propósito:** Muestra una lista de todos los formularios existentes.
*   **Props:**
    *   `forms: Form[]`: Un array de objetos de formulario obtenidos de la API.
*   **Componentes Secundarios:**
    *   `FormCard`: Se renderizará un `FormCard` por cada formulario en la lista.
*   **Funcionalidad y Estado:**
    *   Manejará el estado de carga mientras se obtienen los formularios.
    *   Mostrará un mensaje si no hay formularios.
    *   Tendrá un botón "Crear Nuevo Formulario" que navegará a `/forms/new`.

### 2. `FormCard`

*   **Propósito:** Mostrar una vista previa de un formulario en la `FormsPage`.
*   **Props:**
    *   `form: Form`: El objeto del formulario a mostrar.
*   **Funcionalidad:**
    *   Mostrará el título del formulario y un resumen (ej. "3 respuestas").
    *   Al hacer clic, navegará a la página de visualización del formulario (`/forms/[formId]`).

### 3. `FormEditorPage` (`/forms/new` y `/forms/[formId]/edit`)

*   **Propósito:** Permite a los usuarios crear un nuevo formulario o editar uno existente.
*   **Props:**
    *   `form?: Form`: (Opcional) El objeto del formulario a editar. Si no se proporciona, se asume la creación de un nuevo formulario.
*   **Componentes Secundarios:**
    *   `FormField`: Para cada campo del formulario.
*   **Funcionalidad y Estado:**
    *   Manejará el estado del título del formulario.
    *   Manejará un estado para la lista de campos del formulario (`fields: FormField[]`).
    *   Permitirá añadir, eliminar y reordenar (arrastrar y soltar) los `FormField`.
    *   Tendrá un botón "Guardar" que enviará los datos del formulario a la API.

### 4. `FormField`

*   **Propósito:** Representa un campo individual en el `FormEditorPage`.
*   **Props:**
    *   `field: FormFieldData`: Los datos del campo (etiqueta, tipo, esObligatorio).
    *   `onUpdate: (field: FormFieldData) => void`: Función para actualizar los datos del campo.
    *   `onDelete: () => void`: Función para eliminar el campo.
*   **Funcionalidad:**
    *   Contendrá inputs para editar la etiqueta, seleccionar el tipo de campo (texto, checkbox, radio, etc.) y marcar si es obligatorio.

### 5. `FormViewPage` (`/forms/[formId]`)

*   **Propósito:** Muestra una vista detallada de un formulario, incluyendo sus respuestas.
*   **Props:**
    *   `form: Form`: El objeto del formulario.
    *   `responses: Response[]`: Un array de las respuestas recibidas.
*   **Componentes Secundarios:**
    *   `ResponseCard`: Para mostrar cada respuesta.
*   **Funcionalidad y Estado:**
    *   Mostrará el formulario renderizado (sin inputs, solo visual).
    *   Tendrá un botón "Editar" que navegará a `/forms/[formId]/edit`.
    *   Tendrá un botón "Compartir" que mostrará la URL pública (`/forms/fill/[formId]`).
    *   Listará las respuestas recibidas usando el componente `ResponseCard`.

### 6. `ResponseCard`

*   **Propósito:** Mostrar una respuesta individual en la `FormViewPage`.
*   **Props:**
    *   `response: Response`: El objeto de la respuesta.
*   **Funcionalidad:**
    *   Mostrará un resumen de la respuesta (ej. fecha, y quizás las primeras respuestas).
    *   Podría tener una opción para ver los detalles completos de la respuesta en un modal.

### 7. `PublicFormPage` (`/forms/fill/[formId]`)

*   **Propósito:** Página pública para que los usuarios rellenen y envíen un formulario.
*   **Props:**
    *   `form: Form`: El objeto del formulario a mostrar.
*   **Funcionalidad y Estado:**
    *   Renderizará los campos del formulario con sus respectivos inputs (texto, checkbox, etc.).
    *   Manejará el estado de los valores de los campos del formulario.
    *   Tendrá un botón "Enviar" que enviará las respuestas a la API.
    *   Realizará validaciones (ej. campos obligatorios).

## Diagrama de Flujo de Mermaid

```mermaid
graph TD
    subgraph "Flujo de Usuario"
        A[Usuario visita /forms] --> B{¿Hay formularios?}
        B -- Sí --> C[Ve lista de FormCard]
        B -- No --> D[Ve mensaje "No hay formularios"]
        C --> E{Elige un formulario}
        E -- Clic en FormCard --> F[Navega a /forms/[formId]]
        A --> G[Clic en "Crear Nuevo Formulario"]
        G --> H[Navega a /forms/new]
    end

    subgraph "Página Principal [/forms]"
        FormsPage --> FormCard
    end

    subgraph "Creación/Edición [/forms/new, /forms/[formId]/edit]"
        FormEditorPage --> FormField
    end

    subgraph "Vista de Formulario [/forms/[formId]]"
        FormViewPage --> ResponseCard
    end

    subgraph "Página Pública [/forms/fill/[formId]]"
        PublicFormPage
    end