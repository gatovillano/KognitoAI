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
5.  **RETURN**: Para devolver caminos completos, usa la sintaxis `MATCH p = ... RETURN p`. NUNCA uses funciones inexistentes como `path(n, r, m)`. Si no usas una variable de camino, devuelve `n, r, m`.

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
**Tarea**: Eres un experto en análisis lingüístico y grafos de conocimiento. Tu objetivo es identificar relaciones EXPLICITAS, SIGNIFICATIVAS y NO TRIVIALES entre entidades basándote en el contexto.

**CRITERIOS DE CALIDAD**:
1. **No Trivialidad**: Evita relaciones obvias o de simple mención (ej. MENCIONA, APARECE_CON). Busca verbos de acción, pertenencia, causalidad o influencia.
2. **Especificidad**: Prefiere tipos de relación específicos (ej. LIDERADO_POR) sobre genéricos (ej. RELACIONADO_CON).
3. **Fidelidad**: La relación debe estar CLARAMENTE sustentada por el texto. Si es ambigua, asigna baja confianza o márcala como NO_RELATION.

**Contexto**:
"{context}"

**Pares de Entidades a Analizar**:
{pairs_info}

**Responde ÚNICAMENTE con un objeto JSON siguiendo este formato**:
{{
    "relationships": [
        {{
            "id": "ID original del par",
            "type": "TIPO_EN_MAYUSCULAS",
            "description": "Explicación breve de la conexión real",
            "confidence": 0.0 a 1.0,
            "direction": "a->b" o "b->a"
        }}
    ]
}}

**Nota**: Si un par no tiene una conexión sustancial en este fragmento de texto, usa "NO_RELATION" o simplemente omítelo en la lista.
"""