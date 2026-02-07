# knowledge_graph/knowledge_extraction_node.py

import logging
import json
import asyncio
from typing import Dict, Any, List, Optional
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate

from core.llm_manager import get_fast_llm
from knowledge_graph.graph_database import GraphDB
from knowledge_graph.neo4j_adapter import Neo4jAdapter
from core.config import settings

logger = logging.getLogger(__name__)

KNOWLEDGE_EXTRACTION_PROMPT = """
**Tarea**: Eres un experto en extracción de conocimiento. Tu objetivo es refinar las entidades extraídas y, sobre todo, identificar las RELACIONES significativas entre ellas basándote en la conversación.

**Entidades detectadas previamente (GLiNER)**:
{gliner_entities}

**Instrucciones**:
1. **Refina Entidades**: Revisa las entidades detectadas por GLiNER. Si falta alguna importante (conceptos abstractos, hechos específicos) que no sea una entidad nombrada estándar, añádela.
2. **Extrae Relaciones**: Identifica cómo se conectan las entidades entre sí basándote en el mensaje del usuario y la respuesta del asistente.
   - Cada relación debe tener: `source` (nombre entidad origen), `target` (nombre entidad destino), `type` (MAYÚSCULAS, ej. INTERESTED_IN, WORKS_ON, USES, LIKES), y una breve `description`.
3. **Sé preciso**: No inventes información. Solo extrae lo que es explícito o claramente implícito.

**Interacción**:
- Usuario: "{user_message}"
- Asistente: "{ai_message}"

**Responde ÚNICAMENTE con este formato JSON**:
{{
    "entities": [
        {{
            "name": "Nombre de la entidad",
            "type": "TIPO",
            "description": "Breve descripción"
        }}
    ],
    "relationships": [
        {{
            "source": "Nombre origen",
            "target": "Nombre destino",
            "type": "TIPO_RELACION",
            "description": "Descripción de la conexión"
        }}
    ]
}}
"""

class KnowledgeExtractionNode:
    """
    Nodo de LangGraph que extrae conocimiento usando un enfoque híbrido:
    GLiNER para entidades + LLM para relaciones y refinamiento.
    """

    def __init__(self, graph_db: GraphDB):
        self.graph_db = graph_db
        self.adapter = Neo4jAdapter(graph_db)
        self.llm = get_fast_llm()
        self.gliner_model = None
        self.initialized = False
        
        # Etiquetas para GLiNER
        self.gliner_labels = [
            "person", "organization", "location", "product", "event", 
            "technology", "concept", "methodology", "research_area",
            "skill", "tool", "problem", "solution", "goal"
        ]
        
        logger.info("✅ KnowledgeExtractionNode inicializado.")

    async def _initialize_gliner(self):
        """Inicializa GLiNER si está habilitado en settings."""
        if self.initialized:
            return
            
        if settings.use_gliner:
            try:
                from gliner import GLiNER
                model_map = {
                    "small": "urchade/gliner_small-v2.1",
                    "base": "urchade/gliner_base",
                    "large": "urchade/gliner_large-v2.1"
                }
                model_name = model_map.get(settings.gliner_model_size.lower(), model_map["small"])
                logger.info(f"📥 Cargando GLiNER para extracción en tiempo real: {model_name}")
                self.gliner_model = await asyncio.to_thread(GLiNER.from_pretrained, model_name)
                logger.info("✅ GLiNER cargado exitosamente en el nodo de extracción.")
            except Exception as e:
                logger.error(f"❌ Error cargando GLiNER: {e}")
        
        self.initialized = True

    async def ainvoke(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analiza el último turno de la conversación y guarda el conocimiento en el grafo.
        """
        logger.info("--- (Grafo) Nodo: Extracción de Conocimiento (GLiNER + LLM) ---")
        
        # Asegurar inicialización
        if not self.initialized:
            await self._initialize_gliner()

        messages = state.get("messages", [])
        if len(messages) < 2:
            return state

        user_message = ""
        ai_message = ""
        
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage) and not user_message:
                user_message = str(msg.content)
            if isinstance(msg, AIMessage) and not ai_message:
                ai_message = str(msg.content)
            if user_message and ai_message:
                break

        if not user_message or not ai_message:
            return state

        # 1. Extracción Zero-Shot con GLiNER (Entidades base)
        gliner_entities = []
        if self.gliner_model:
            try:
                combined_text = f"{user_message} {ai_message}"
                # GLiNER tiene un límite de tokens, truncamos para seguridad
                truncated_text = combined_text[:1000]
                entities = await asyncio.to_thread(
                    self.gliner_model.predict_entities,
                    truncated_text,
                    self.gliner_labels,
                    threshold=settings.gliner_threshold
                )
                gliner_entities = [
                    {"name": ent["text"], "type": ent["label"], "score": ent["score"]}
                    for ent in entities
                ]
                logger.info(f"GLiNER detectó {len(gliner_entities)} entidades.")
            except Exception as e:
                logger.warning(f"Error en predicción GLiNER: {e}")

        # 2. Refinamiento y Relaciones con LLM
        extracted_data = await self._refine_with_llm(user_message, ai_message, gliner_entities)
        if not extracted_data:
            return state

        # 3. Persistir en Neo4j
        await self._persist_knowledge(extracted_data, state)

        return state

    async def _refine_with_llm(self, user_msg: str, ai_msg: str, gliner_ents: List[Dict]) -> Optional[Dict]:
        """Usa el LLM para conectar las entidades y extraer relaciones."""
        if not self.llm:
            return None

        prompt = ChatPromptTemplate.from_template(KNOWLEDGE_EXTRACTION_PROMPT)
        chain = prompt | self.llm
        
        try:
            gliner_json = json.dumps(gliner_ents, ensure_ascii=False, indent=2)
            response = await chain.ainvoke({
                "gliner_entities": gliner_json,
                "user_message": user_msg[:1000],
                "ai_message": ai_msg[:2000]
            })
            
            content = str(response.content).strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            
            return json.loads(content.strip())
        except Exception as e:
            logger.error(f"Error refinando con LLM: {e}")
            return None

    def _generate_id(self, name: str, type_: str) -> str:
        """Genera un ID consistente con Neo4jAdapter."""
        normalized_name = name.lower().replace(" ", "_").replace("-", "_")
        return f"entity_{normalized_name}"

    async def _persist_knowledge(self, data: Dict[str, Any], state: Dict[str, Any]):
        """Guarda las entidades y relaciones en Neo4j."""
        account_id = state.get("account_id")
        workspace_id = state.get("workspace_id")
        # Nombre del dataset más amigable para la visualización en la UI
        dataset_name = "Agent Memories"

        entities = data.get("entities", [])
        relationships = data.get("relationships", [])

        if not entities and not relationships:
            return

        # Mapa para buscar IDs por nombre de entidad para las relaciones
        # Clave: nombre original, Valor: ID generado
        name_to_id_map = {}

        formatted_entities = []
        for ent in entities:
            name = ent.get("name")
            type_ = ent.get("type", "ENTITY").upper()
            
            if not name:
                continue
                
            entity_id = self._generate_id(name, type_)
            name_to_id_map[name] = entity_id
            
            formatted_entities.append({
                "id": entity_id, # ID explícito
                "type": type_,
                "name": name, # Top level name
                "dataset_name": dataset_name, # Top level dataset_name
                "properties": {
                    "name": name,
                    "description": ent.get("description"),
                    "account_id": account_id,
                    "workspace_id": workspace_id,
                    "dataset_name": dataset_name
                }
            })

        formatted_relationships = []
        for rel in relationships:
            source_name = rel.get("source")
            target_name = rel.get("target")
            
            # Intentar resolver IDs
            source_id = name_to_id_map.get(source_name)
            target_id = name_to_id_map.get(target_name)
            
            # Si no encontramos el ID en las entidades extraídas, intentamos generarlo
            # asumiendo un tipo genérico o intentando inferirlo (limitación actual)
            # Para mayor robustez, si la entidad no está en la lista 'entities', 
            # deberíamos quizás crearla o ignorar la relación.
            # Por ahora, generaremos un ID asumiendo que si existiera tendría ese formato.
            # Pero esto es arriesgado si no sabemos el tipo.
            # Mejor estrategia: Solo crear relación si ambas entidades están en el lote actual
            # O si podemos confiar en que existen.
            
            if source_id and target_id:
                formatted_relationships.append({
                    "source_id": source_id,
                    "target_id": target_id,
                    "type": rel.get("type", "RELATED_TO").upper(),
                    "dataset_name": dataset_name, # Top level dataset_name
                    "properties": {
                        "description": rel.get("description"),
                        "account_id": account_id,
                        "workspace_id": workspace_id,
                        "dataset_name": dataset_name
                    }
                })

        try:
            await self.adapter.add_cognee_results_to_graph(
                entities=formatted_entities,
                relationships=formatted_relationships,
                account_id=account_id,
                workspace_id=workspace_id
            )
            logger.info(f"✅ Conocimiento persistido: {len(formatted_entities)} entidades, {len(formatted_relationships)} relaciones.")
        except Exception as e:
            logger.error(f"Error persistiendo conocimiento: {e}")
