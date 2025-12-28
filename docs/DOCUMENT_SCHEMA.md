# Esquema del Nodo DOCUMENT y sus Relaciones en Neo4j

Este documento detalla el esquema propuesto para el nodo `DOCUMENT` y las relaciones asociadas en la base de datos Neo4j.

## 1. Nodo: DOCUMENT

El nodo `DOCUMENT` representa un documento procesado dentro del sistema.

### Propiedades:

*   **`id`**: `UUID` (Identificador único universal para el documento. Clave primaria.)
*   **`title`**: `String` (Título del documento.)
*   **`url`**: `String` (URL de origen del documento, si aplica.)
*   **`content_hash`**: `String` (Hash del contenido del documento para verificar integridad o duplicados.)
*   **`summary`**: `String` (Resumen generado por un modelo de lenguaje (LLM) del contenido del documento.)
*   **`keywords`**: `List<String>` (Lista de palabras clave generadas por un LLM, relevantes para el contenido del documento.)
*   **`embedding`**: `List<Float>` (Vector de embedding del contenido del documento, utilizado para cálculos de similitud.)
*   **`topic`**: `String` (Clasificación temática del documento, utilizada para agrupación y relaciones dinámicas.)
*   **`publication_date`**: `DateTime` (Fecha de publicación original del documento.)
*   **`author`**: `String` (Autor o fuente del documento.)
*   **`source_type`**: `String` (Tipo de fuente del documento, e.g., "web", "pdf", "manual_entry".)
*   **`created_at`**: `DateTime` (Marca de tiempo de creación del nodo en la base de datos.)
*   **`updated_at`**: `DateTime` (Marca de tiempo de la última actualización del nodo en la base de datos.)
*   **`workspace_id`**: `UUID` (Identificador del espacio de trabajo al que pertenece el documento.)
*   **`account_id`**: `UUID` (Identificador de la cuenta propietaria del documento.)
*   **`type`**: `String` (Tipo de nodo, siempre "DOCUMENT".)

## 2. Relaciones del Nodo DOCUMENT

El nodo `DOCUMENT` puede establecer las siguientes relaciones con otros nodos:

### 2.1. `CONTAINS_QUOTE`

*   **Descripción**: Relación desde un `DOCUMENT` a un nodo `CONCEPTUAL_QUOTE`, indicando que el documento contiene una cita específica.
*   **Origen**: `DOCUMENT`
*   **Destino**: `CONCEPTUAL_QUOTE`
*   **Propiedades de la Relación**:
    *   **`position_in_document`**: `Integer` (La posición relativa de la cita dentro del documento.)
    *   **`page_number`**: `Integer` (El número de página donde se encuentra la cita, si el documento tiene paginación.)
*   **Restricción para `CONCEPTUAL_QUOTE`**: El nodo `CONCEPTUAL_QUOTE` debe tener un atributo `source_document_id` que referencie el `id` del `DOCUMENT` de origen.

### 2.2. `HAS_IDEA_PROFILE`

*   **Descripción**: Relación desde un `DOCUMENT` a un nodo `IDEA_PROFILE`, indicando la contribución del documento a un perfil de ideas.
*   **Origen**: `DOCUMENT`
*   **Destino**: `IDEA_PROFILE`
*   **Propiedades de la Relación**:
    *   **`contribution_score`**: `Float` (Puntuación que indica la importancia o relevancia del documento para el perfil de ideas.)
    *   **`relevant_quotes_count`**: `Integer` (Número de citas relevantes dentro de este documento que contribuyen al perfil de ideas.)

### 2.3. `MISMO_TOPICO_(NOMBRETOPICO)`

*   **Descripción**: Relación dinámica entre dos nodos `DOCUMENT` que comparten el mismo tópico. El nombre de la relación se construye con el valor del atributo `topic`.
    *   **Ejemplo**: Si el `topic` es "InteligenciaArtificial", la relación será `MISMO_TOPICO_InteligenciaArtificial`.
*   **Origen**: `DOCUMENT`
*   **Destino**: `DOCUMENT`
*   **Propiedades de la Relación**:
    *   **`similarity_score`**: `Float` (Puntuación de similitud entre los documentos basada en su contenido o características.)
    *   **`topic`**: `String` (El tópico común que comparten ambos documentos.)

### 2.4. `RELATED_TO_DOCUMENT`

*   **Descripción**: Relación general entre dos nodos `DOCUMENT` que están relacionados por contenido, embeddings o ideas compartidas.
*   **Origen**: `DOCUMENT`
*   **Destino**: `DOCUMENT`
*   **Propiedades de la Relación**:
    *   **`similarity_score`**: `Float` (Puntuación de similitud entre los embeddings de los documentos.)
    *   **`shared_ideas_count`**: `Integer` (Número de ideas o conceptos que ambos documentos tienen en común.)
    *   **`reason`**: `String` (Explicación textual de la razón de la relación, generada por un LLM o lógica de negocio.)