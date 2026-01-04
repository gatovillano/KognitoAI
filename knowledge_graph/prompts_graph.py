# knowledge_graph/prompts_graph.py

"""
Módulo para almacenar los prompts especializados para la interacción con el grafo de conocimiento.
"""

# Prompt principal para la generación de consultas Cypher.
# Este prompt es la "receta" que le damos al LLM para que traduzca lenguaje natural a Cypher.
CYPHER_GENERATION_PROMPT = """
**Tarea**: Eres un experto en Neo4j y tu única función es generar consultas Cypher a partir de la pregunta de un usuario y el schema de la base de datos.

**Instrucciones Cruciales**:
1.  **Solo Cypher**: Tu respuesta DEBE contener únicamente la consulta Cypher. No incluyas explicaciones.
2.  **Schema es Rey**: Basa tu consulta ESTRICTAMENTE en el schema proporcionado.
3.  **Filtrado por Dataset**: El grafo contiene diferentes tipos de información identificados por la propiedad `dataset_name`:
    - `Agent Memories`: Contiene la historia de la conversación, preferencias y hechos sobre el usuario.
    - Otros nombres (ej. `conceptual_graph`): Contienen conocimientos extraídos de documentos subidos.
    - **IMPORTANTE**: Si la pregunta es personal o sobre el historial, filtra por `dataset_name = 'Agent Memories'`. Si es técnica o sobre documentos, usa el dataset correspondiente o no filtres si no estás seguro.
4.  **Relaciones Variables**: Utiliza `[r*1..2]` para explorar conexiones.
5.  **RETURN**: Siempre devuelve el `path` o los nodos y relaciones (`n, r, m`).

**Schema de la Base de Datos**:
```
{schema}
```

**Pregunta del Usuario**:
"{question}"

**Consulta Cypher (solo el código)**:
"""

# Prompt para resumir los resultados del grafo en un formato legible.
GRAPH_SUMMARY_PROMPT = """
**Tarea**: Eres un analista de datos y tu función es resumir los resultados de una consulta a un grafo de conocimiento en un texto claro, conciso y valioso para un usuario.

**Instrucciones**:
1.  **Síntesis**: No te limites a listar los datos. Sintetiza la información, destaca las conexiones clave y los insights más importantes.
2.  **Lenguaje Natural**: Escribe en un lenguaje natural y fácil de entender, como si se lo explicaras a alguien no técnico.
3.  **Enfócate en la Pregunta**: Asegúrate de que tu resumen responda directamente a la pregunta original del usuario.
4.  **No Exageres**: Basa tu resumen únicamente en los datos proporcionados. No inventes información.

**Pregunta Original del Usuario**:
"{question}"

**Resultados de la Consulta al Grafo (en formato JSON)**:
```json
{results}
```

**Resumen Analítico (en texto plano)**:
"""

# Prompt para extraer relaciones ricas entre entidades basadas en su contexto.
RELATIONSHIP_EXTRACTION_PROMPT = """
**Tarea**: Eres un experto en análisis lingüístico y grafos de conocimiento. Tu objetivo es identificar la relación exacta y significativa entre pares de entidades basándote ESTRICTAMENTE en el contexto proporcionado.

**Instrucciones**:
1.  **Análisis de Contexto**: Lee el fragmento de texto y determina cómo se relacionan las dos entidades mencionadas.
2.  **Tipo de Relación**: Define un tipo de relación corto y en mayúsculas (ej. WORKS_AT, CREATED_BY, USES_TECHNOLOGY, LOCATED_IN, PART_OF, INFLUENCES). Sé específico.
3.  **Descripción**: Escribe una breve oración que explique la relación (ej. "Elon Musk es el fundador de SpaceX").
4.  **Confianza**: Asigna un valor de 0.0 a 1.0 según qué tan explícita es la relación en el texto.
5.  **Dirección**: Identifica claramente cuál es la entidad origen (source) y cuál la destino (target).

**Contexto**:
"{context}"

**Pares de Entidades a Analizar**:
{pairs_info}

**Instrucciones**:
1. Para cada par, identifica si existe una relación explícita en el texto.
2. Si existe, define:
   - `type`: Un tipo de relación corto en MAYÚSCULAS (ej. WORKS_AT, USES, PART_OF, CREATED_BY, INFLUENCES).
   - `description`: Una oración breve explicando la relación.
   - `confidence`: Un valor entre 0.0 y 1.0.
   - `direction`: Indica si la relación es de la primera entidad (a) hacia la segunda (b) ("a->b") o de la segunda (b) hacia la primera (a) ("b->a").
3. Si no hay una relación clara para un par, puedes omitirlo o establecer `type` como "NO_RELATION".
4. Considera los siguientes tipos de relaciones comunes para mejorar la consistencia: "WORKS_AT", "PART_OF", "USES", "CREATED_BY", "INFLUENCES", "LOCATED_IN", "IS_A", "HAS_PROPERTY", "PERFORMS", "ASSOCIATED_WITH".

**Responde ÚNICAMENTE con un objeto JSON que contenga una lista "relationships"**. Cada elemento de la lista debe tener el siguiente formato:
{{
    "id": "ID original del par de entidades",
    "type": "TIPO_DE_RELACION",
    "description": "Descripción clara de la relación",
    "confidence": 0.95,
    "direction": "a->b" o "b->a"
}}
"""