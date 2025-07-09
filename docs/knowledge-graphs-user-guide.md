# Guía de Usuario: Grafos de Conocimiento en KognitoAI

## 🎯 Introducción

Los grafos de conocimiento en KognitoAI te permiten crear representaciones visuales y navegables de la información contenida en tus documentos y conversaciones. Esta funcionalidad transforma texto plano en redes de conceptos interconectados que puedes explorar y consultar de manera inteligente.

## 🚀 Primeros Pasos

### ¿Qué son los Grafos de Conocimiento?

Un grafo de conocimiento es una red de entidades (conceptos, personas, lugares) conectadas por relaciones significativas. Por ejemplo:

```
Inteligencia Artificial → INCLUYE → Machine Learning
Machine Learning → UTILIZA → Algoritmos
Algoritmos → PROCESAN → Datos
```

### Beneficios

- **Memoria Estructurada**: Organiza información de manera lógica y navegable
- **Descubrimiento de Conexiones**: Encuentra relaciones ocultas entre conceptos
- **Búsquedas Inteligentes**: Consultas más precisas basadas en contexto
- **Visualización**: Mapas mentales y diagramas interactivos

## 🛠️ Herramientas Disponibles

### 1. Análisis de Texto con Grafo de Conocimiento

**Comando**: `text_to_knowledge_graph`

**¿Cuándo usar?**: Para analizar textos y crear grafos de conocimiento automáticamente.

**Ejemplo de uso**:
```
Analiza este texto y crea un grafo de conocimiento:

"La inteligencia artificial es una rama de la informática que incluye 
subcampos como machine learning, procesamiento de lenguaje natural y 
visión por computadora. El machine learning utiliza algoritmos para 
permitir que las máquinas aprendan de los datos."
```

**Resultado esperado**:
- Análisis completo del texto (resumen, temas, sentimiento)
- Grafo con entidades: "Inteligencia Artificial", "Machine Learning", "Algoritmos"
- Relaciones: "IA incluye ML", "ML utiliza Algoritmos"

### 2. Mapa Mental con Grafo Persistente

**Comando**: `mindmap_to_knowledge_graph`

**¿Cuándo usar?**: Para documentos complejos que necesitan visualización jerárquica.

**Ejemplo de uso**:
```
Genera un mapa mental y grafo de conocimiento de este documento sobre cambio climático:

"El cambio climático tiene múltiples causas como emisiones de CO2, 
deforestación e industrialización. Los efectos incluyen aumento de 
temperaturas y derretimiento de glaciares. Las soluciones incluyen 
energías renovables y políticas ambientales."
```

**Resultado esperado**:
- Mapa mental visual con "Cambio Climático" como centro
- Ramas para "Causas", "Efectos", "Soluciones"
- Grafo persistente en Neo4j para consultas futuras

## 📋 Casos de Uso Prácticos

### Caso 1: Análisis de Documentos de Investigación

**Situación**: Tienes un paper académico sobre inteligencia artificial.

**Proceso**:
1. Usa `text_to_knowledge_graph` con el contenido completo
2. Especifica `use_cognee=true` para análisis avanzado
3. Asigna un `workspace_id` específico para tu proyecto de investigación

**Comando**:
```
Analiza este paper de IA y crea un grafo de conocimiento avanzado:
[contenido del paper]

Configuración:
- workspace: "investigacion_ia"
- usar cognee: sí
- nombre del grafo: "paper_transformers_2024"
```

### Caso 2: Mapas Mentales de Reuniones

**Situación**: Notas de una reunión de planificación estratégica.

**Proceso**:
1. Usa `mindmap_to_knowledge_graph` con las notas
2. Proporciona un `topic_hint` claro
3. Especifica `concept_query` para extraer decisiones y acciones

**Comando**:
```
Crea un mapa mental de esta reunión de planificación:
[notas de la reunión]

Configuración:
- tema principal: "Planificación Q1 2024"
- extraer: "decisiones, acciones, responsables y fechas"
- workspace: "equipo_direccion"
```

### Caso 3: Base de Conocimiento Empresarial

**Situación**: Múltiples documentos de políticas y procedimientos.

**Proceso**:
1. Procesa cada documento con `text_to_knowledge_graph`
2. Usa el mismo `workspace_id` para todos
3. Nombres de grafo descriptivos para cada área

**Comandos secuenciales**:
```
# Documento 1
Analiza esta política de RRHH y crea grafo:
[contenido política RRHH]
workspace: "empresa_conocimiento"
grafo: "politicas_rrhh"

# Documento 2  
Analiza este procedimiento de ventas y crea grafo:
[contenido procedimiento ventas]
workspace: "empresa_conocimiento"
grafo: "procedimientos_ventas"
```

## 🔍 Consultas y Búsquedas

### Búsquedas Básicas

Una vez creados los grafos, puedes hacer consultas como:

```
"¿Qué conceptos están relacionados con machine learning en mi workspace de investigación?"

"Muéstrame todas las decisiones tomadas en las reuniones del Q1"

"¿Cuáles son los procedimientos relacionados con atención al cliente?"
```

### Búsquedas Avanzadas

Para consultas más específicas:

```
"Encuentra la ruta más corta entre 'Inteligencia Artificial' y 'Ética' en mis grafos"

"¿Qué conceptos aparecen en múltiples documentos de mi workspace?"

"Muéstrame los conceptos más centrales en mi base de conocimiento"
```

## ⚙️ Configuración Avanzada

### Parámetros Importantes

#### workspace_id
- **Propósito**: Organizar grafos por proyecto o área
- **Recomendación**: Usa nombres descriptivos como "investigacion_ia", "proyecto_alpha"
- **Ejemplo**: `workspace_id: "marketing_2024"`

#### graph_name
- **Propósito**: Identificar grafos específicos dentro de un workspace
- **Recomendación**: Incluye fecha o versión
- **Ejemplo**: `graph_name: "analisis_competencia_enero_2024"`

#### use_cognee
- **Cuándo activar**: Para análisis semántico avanzado
- **Beneficios**: Mejor extracción de entidades y relaciones
- **Costo**: Mayor tiempo de procesamiento

### Mejores Prácticas

#### 1. Organización por Workspace
```
investigacion/
├── papers_ia/
├── papers_ml/
└── papers_nlp/

empresa/
├── politicas/
├── procedimientos/
└── estrategia/
```

#### 2. Nombres Descriptivos
- ✅ Bueno: `"reunion_planificacion_q1_2024"`
- ❌ Malo: `"reunion1"`

#### 3. Procesamiento Incremental
- Procesa documentos uno por uno
- Usa el mismo workspace para temas relacionados
- Revisa y ajusta según resultados

## 🎨 Visualización

### Acceso a Neo4j Browser

1. Abre http://localhost:7474 en tu navegador
2. Credenciales:
   - Usuario: `neo4j`
   - Contraseña: `Kn0wl3dg3Gr4ph2024!`

### Consultas Visuales Básicas

```cypher
-- Ver todos tus nodos
MATCH (n) 
WHERE n.account_id = "tu_account_id"
RETURN n
LIMIT 50

-- Ver conceptos de un workspace específico
MATCH (n:Concept) 
WHERE n.workspace_id = "investigacion_ia"
RETURN n

-- Ver relaciones entre conceptos
MATCH (c1:Concept)-[r]-(c2:Concept)
WHERE c1.account_id = "tu_account_id"
RETURN c1, r, c2
LIMIT 20
```

## 🚨 Solución de Problemas

### Problemas Comunes

#### "No se pudieron extraer conceptos"
**Causa**: Texto muy corto o sin estructura clara
**Solución**: 
- Usa textos de al menos 100 palabras
- Proporciona `topic_hint` más específico
- Ajusta `concept_query` para ser más específico

#### "Error de conexión con Neo4j"
**Causa**: Servicio Neo4j no está corriendo
**Solución**:
```bash
docker-compose up -d neo4j
docker-compose ps neo4j
```

#### "Timeout en procesamiento"
**Causa**: Documento muy largo o Cognee sobrecargado
**Solución**:
- Divide documentos largos en secciones
- Usa `use_cognee=false` para procesamiento más rápido
- Intenta nuevamente después de unos minutos

### Verificación del Sistema

Para verificar que todo funciona correctamente:

```
Ejecuta una prueba simple:

"Analiza este texto corto y crea un grafo: 'Los gatos son animales domésticos que pertenecen a la familia de los felinos. Son carnívoros y excelentes cazadores.'"
```

Deberías obtener:
- Análisis del texto exitoso
- Al menos 2-3 conceptos extraídos
- 1-2 relaciones creadas
- Confirmación de almacenamiento en Neo4j

## 📞 Soporte

### Logs y Debugging

Si encuentras problemas, puedes:

1. **Revisar logs del sistema**
2. **Ejecutar script de diagnóstico**: `python test_knowledge_graph_tools.py`
3. **Verificar servicios**: `docker-compose ps`

### Contacto

Para soporte técnico o preguntas avanzadas, consulta:
- Documentación técnica: `docs/knowledge-graphs-technical-guide.md`
- Guía de integración: `docs/knowledge-graphs-integration.md`

---

**¡Disfruta explorando tus grafos de conocimiento!** 🧠✨

**Versión**: 1.0  
**Última Actualización**: 2025-01-09
