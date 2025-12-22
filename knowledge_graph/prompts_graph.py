# knowledge_graph/prompts_graph.py

"""
Módulo para almacenar los prompts especializados para la interacción con el grafo de conocimiento.
"""

# Prompt principal para la generación de consultas Cypher.
# Este prompt es la "receta" que le damos al LLM para que traduzca lenguaje natural a Cypher.
CYPHER_GENERATION_PROMPT = """
**Tarea**: Eres un experto en Neo4j y tu única función es generar consultas Cypher a partir de la pregunta de un usuario y el schema de la base de datos.

**Instrucciones Cruciales**:
1.  **Solo Cypher**: Tu respuesta DEBE contener únicamente la consulta Cypher. No incluyas explicaciones, saludos, ni texto introductorio como "Aquí está la consulta:".
2.  **Schema es Rey**: Basa tu consulta ESTRICTAMENTE en el schema proporcionado. No inventes tipos de nodos o relaciones que no existan en el schema.
3.  **Relaciones Variables**: Utiliza `[r*1..2]` o `[r*1..3]` para explorar relaciones a 1, 2 o 3 saltos. Esto es vital para encontrar conexiones no directas.
4.  **Propiedades**: Utiliza las propiedades de los nodos (`name`, `id`, `type`, `description`) para filtrar los resultados. Presta especial atención a la propiedad `name`.
5.  **Ambigüedad**: Si la pregunta es ambigua, genera una consulta que sea lo más amplia y útil posible. Es mejor devolver más resultados que menos.
6.  **Complejidad**: No dudes en usar `MATCH`, `WHERE`, `WITH`, `UNWIND` y `RETURN` para crear consultas complejas y eficientes.
7.  **RETURN**: Siempre devuelve el `path` o los nodos y relaciones (`n, r, m`) para que se pueda reconstruir el subgrafo.

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