# knowledge_graph/knowledge_extraction_node.py

import logging
import json
import asyncio
import uuid
from typing import Dict, Any, List, Optional
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate

from core.llm_manager import get_fast_llm
from knowledge_graph.graph_database import GraphDB
from knowledge_graph.neo4j_adapter import Neo4jAdapter
from core.config import settings

logger = logging.getLogger(__name__)

KNOWLEDGE_EXTRACTION_PROMPT = """
**Tarea**: Eres un experto en extracción de conocimiento y síntesis conceptual. Tu objetivo es transformar la conversación en un grafo de conocimiento rico que capture tanto detalles granulares como ideas de gran envergadura (Conceptual Insights).

**CONTEXTO CRÍTICO DE PROYECTO / WORKSPACE**:
- El proyecto y workspace actual en el que estás trabajando es: "{workspace_name}".
- Todas las entidades, conceptos, citas y relaciones deben pertenecer estrictamente a este proyecto y workspace. No asumas ni generes relaciones con elementos que pertenezcan a otros proyectos o que sean externos al contexto de "{workspace_name}". Evita mezclar proyectos.

**Instrucciones**:
1. **Identifica Entidades (Micro)**: Personas, organizaciones, tecnologías, herramientas, etc.
2. **Extrae Citas Conceptuales (Macro)**: Busca "Ideas Maestras", conclusiones estratégicas o citas de gran envergadura que el usuario o el asistente hayan expresado. No te limites a palabras sueltas; captura la frase o párrafo que contiene la "esencia" de la idea.
   - Estas se etiquetarán como `CONCEPTUAL_QUOTE`.
3. **Define Relaciones**: Conecta las entidades y las citas conceptuales. 
   - Usa tipos como `REFINES`, `PROPOSES`, `CONTRADICTS`, `SUPPORTS`, `PART_OF`.
4. **Perfiles de Idea**: Si detectas un conjunto de ideas relacionadas que forman un concepto mayor, identifícalo como un perfil de idea central (`IDEA_PROFILE`).

**Interacción Actual**:
- Usuario: "{user_message}"
- Asistente: "{ai_message}"

**Previas Entidades detectadas (Sugerencia)**:
{gliner_entities}

**Responde ÚNICAMENTE con este formato JSON**:
{{
    "conceptual_insights": [
        {{
            "concept": "Nombre del concepto/idea principal",
            "full_text": "La cita completa o idea de gran envergadura expresada",
            "category": "teoría/estrategia/metodología/conclusión",
            "importance": "alta/media"
        }}
    ],
    "entities": [
        {{
            "name": "Nombre entidad",
            "type": "TIPO",
            "description": "Contexto"
        }}
    ],
    "relationships": [
        {{
            "source": "Nombre origen",
            "target": "Nombre destino",
            "type": "TIPO_RELACION",
            "description": "Por qué se conectan"
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
        account_id = state.get("account_id")
        workspace_id = state.get("workspace_id")
        
        # Obtener nombre de workspace
        workspace_name = None
        if workspace_id:
            try:
                from core.database import SessionLocal, Workspace
                from sqlalchemy import select
                async with SessionLocal() as db_session:
                    stmt = select(Workspace).where(Workspace.id == (uuid.UUID(workspace_id) if isinstance(workspace_id, str) else workspace_id))
                    res = await db_session.execute(stmt)
                    workspace_obj = res.scalar_one_or_none()
                    if workspace_obj:
                        workspace_name = workspace_obj.name
                        logger.info(f"💼 Workspace resolved to name: '{workspace_name}'")
            except Exception as e:
                logger.error(f"Error resolviendo workspace_name en KnowledgeExtractionNode: {e}")

        # Intentar obtener un LLM específico para el usuario si está disponible
        llm_to_use = self.llm
        if account_id:
            from core.llm_manager import get_llm_for_user
            user_llm = await get_llm_for_user(account_id, purpose="fast")
            if user_llm:
                llm_to_use = user_llm

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
        extracted_data = await self._refine_with_llm(user_message, ai_message, gliner_entities, llm=llm_to_use, workspace_name=workspace_name)
        if not extracted_data:
            return state

        # 3. Persistir en Neo4j
        await self._persist_knowledge(extracted_data, state, workspace_name=workspace_name)

        return state

    async def _refine_with_llm(self, user_msg: str, ai_msg: str, gliner_ents: List[Dict], llm: Optional[Any] = None, workspace_name: Optional[str] = None) -> Optional[Dict]:
        """Usa el LLM para conectar las entidades y extraer relaciones."""
        llm_to_use = llm or self.llm
        if not llm_to_use:
            return None

        prompt = ChatPromptTemplate.from_template(KNOWLEDGE_EXTRACTION_PROMPT)
        chain = prompt | llm_to_use
        
        try:
            gliner_json = json.dumps(gliner_ents, ensure_ascii=False, indent=2)
            response = await chain.ainvoke({
                "gliner_entities": gliner_json,
                "user_message": user_msg[:1000],
                "ai_message": ai_msg[:2000],
                "workspace_name": workspace_name or "General / Desconocido"
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

    async def _persist_knowledge(self, data: Dict[str, Any], state: Dict[str, Any], workspace_name: Optional[str] = None):
        """Guarda las entidades, relaciones y citas conceptuales en Neo4j."""
        account_id = state.get("account_id")
        workspace_id = state.get("workspace_id")
        # Nombre del dataset para memorias conversacionales (aislado por account_id y workspace_id en las propiedades)
        dataset_name = "Agent Memories"

        entities = data.get("entities", [])
        relationships = data.get("relationships", [])
        conceptual_insights = data.get("conceptual_insights", [])

        if not entities and not relationships and not conceptual_insights:
            return

        # Mapa para buscar IDs por nombre de entidad/concepto
        name_to_id_map = {}
        formatted_entities = []

        # 1. Procesar Entidades Granulares
        for ent in entities:
            name = ent.get("name")
            type_ = ent.get("type", "ENTITY").upper()
            if not name: continue
                
            entity_id = self._generate_id(name, type_)
            name_to_id_map[name] = entity_id
            
            formatted_entities.append({
                "id": entity_id,
                "type": type_,
                "name": name,
                "dataset_name": dataset_name,
                "workspace": workspace_name,
                "properties": {
                    "name": name,
                    "description": ent.get("description"),
                    "account_id": account_id,
                    "workspace_id": workspace_id,
                    "workspace": workspace_name,
                    "dataset_name": dataset_name,
                    "source": "conversation"
                }
            })

        # 2. Procesar Citas Conceptuales (Ideas de Envergadura)
        for insight in conceptual_insights:
            concept = insight.get("concept")
            full_text = insight.get("full_text")
            if not concept or not full_text: continue

            insight_id = f"insight_{uuid.uuid4().hex[:12]}"
            name_to_id_map[concept] = insight_id

            formatted_entities.append({
                "id": insight_id,
                "type": "CONCEPTUAL_QUOTE",
                "name": concept,
                "dataset_name": dataset_name,
                "workspace": workspace_name,
                "properties": {
                    "name": concept,
                    "concept": concept,
                    "full_text": full_text,
                    "category": insight.get("category", "general"),
                    "importance": insight.get("importance", "media"),
                    "account_id": account_id,
                    "workspace_id": workspace_id,
                    "workspace": workspace_name,
                    "dataset_name": dataset_name,
                    "source": "conversation_insight"
                }
            })

        # 3. Procesar Relaciones
        formatted_relationships = []
        for rel in relationships:
            source_name = rel.get("source")
            target_name = rel.get("target")
            
            source_id = name_to_id_map.get(source_name)
            target_id = name_to_id_map.get(target_name)
            
            if source_id and target_id:
                formatted_relationships.append({
                    "source_id": source_id,
                    "target_id": target_id,
                    "type": rel.get("type", "RELATED_TO").upper(),
                    "dataset_name": dataset_name,
                    "workspace": workspace_name,
                    "properties": {
                        "description": rel.get("description"),
                        "account_id": account_id,
                        "workspace_id": workspace_id,
                        "workspace": workspace_name,
                        "dataset_name": dataset_name
                    }
                })

        try:
            await self.adapter.add_cognee_results_to_graph(
                entities=formatted_entities,
                relationships=formatted_relationships,
                account_id=account_id,
                workspace_id=workspace_id,
                workspace=workspace_name
            )
            logger.info(f"✅ Conocimiento persistido: {len(formatted_entities)} entidades/insights, {len(formatted_relationships)} relaciones.")
        except Exception as e:
            logger.error(f"Error persistiendo conocimiento: {e}")
