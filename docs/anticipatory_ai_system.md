# Sistema de IA Anticipatoria para KognitoAI

## 1. Concepto y Arquitectura General

Un **sistema anticipatorio** (proactive AI) va más allá del modelo reactivo tradicional donde el usuario pregunta y el agente responde. En su lugar, el agente:

1. **Monitoriza patrones** en el comportamiento y contexto del usuario
2. **Predice necesidades futuras** basándose en datos históricos y contexto actual
3. **Genera insights proactivamente** antes de que se soliciten
4. **Ejecuta acciones preventivas** automáticamente cuando detecta oportunidades o riesgos

### Arquitectura en Capas del Sistema Anticipatorio

```
┌─────────────────────────────────────────────────────────────┐
│                    CAPA DE INTERFAZ                          │
│    (WebSocket, Notificaciones, Dashboard Insights)           │
├─────────────────────────────────────────────────────────────┤
│                  CAPA DE INSIGHTS                             │
│    (Generador de Patrones, Motor de Predicciones,           │
│     Alertador Inteligente, Generador de Recomendaciones)    │
├─────────────────────────────────────────────────────────────┤
│                  CAPA DE CONTEXTO                            │
│    (Graph de Conocimiento, Memoria Enhanced,                │
│     Perfil de Usuario, Contexto Temporal)                  │
├─────────────────────────────────────────────────────────────┤
│                    CAPA DE DATOS                             │
│    (PostgreSQL, Neo4j, VectorDB, Memoria Conversacional)     │
└─────────────────────────────────────────────────────────────┘
```

## 2. Componentes Principales

### 2.1 Pattern Recognition Engine (Motor de Reconocimiento de Patrones)

```python
# core/anticipation/pattern_recognition.py

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import json
from collections import defaultdict

@dataclass
class Pattern:
    """Representa un patrón detectado en el comportamiento del usuario."""
    name: str
    frequency: float  # Frecuencia del patrón (0-1)
    confidence: float  # Confianza en la detección (0-1)
    trigger_conditions: Dict[str, Any]
    predicted_outcome: str
    last_observed: datetime
    occurrence_count: int

@dataclass
class UserPatternContext:
    """Contexto de patrones para un usuario específico."""
    user_id: str
    behavioral_patterns: List[Pattern] = field(default_factory=list)
    temporal_patterns: Dict[str, List[datetime]] = field(default_factory=dict)
    content_preferences: Dict[str, float] = field(default_factory=dict)
    interaction_style: Dict[str, Any] = field(default_factory=dict)

class PatternRecognitionEngine:
    """
    Motor que identifica patrones en el comportamiento del usuario
    para anticipar necesidades futuras.
    """
    
    def __init__(self, db_session):
        self.db = db_session
        self.patterns_cache = {}  # Cache en memoria para patrones frecuentes
        self.min_confidence_threshold = 0.7
        self.min_occurrence_threshold = 3
    
    async def analyze_user_behavior(
        self, 
        user_id: str, 
        interaction_history: List[Dict]
    ) -> List[Pattern]:
        """
        Analiza el historial de interacciones para detectar patrones.
        
        Args:
            user_id: Identificador del usuario
            interaction_history: Lista de interacciones previas
            
        Returns:
            Lista de patrones detectados ordenados por confianza
        """
        patterns = []
        
        # 1. Detectar patrones temporales
        temporal_patterns = self._detect_temporal_patterns(interaction_history)
        patterns.extend(temporal_patterns)
        
        # 2. Detectar patrones de contenido
        content_patterns = self._detect_content_patterns(interaction_history)
        patterns.extend(content_patterns)
        
        # 3. Detectar patrones de consulta
        query_patterns = self._detect_query_patterns(interaction_history)
        patterns.extend(query_patterns)
        
        # 4. Filtrar por confianza mínima
        filtered_patterns = [
            p for p in patterns 
            if p.confidence >= self.min_confidence_threshold
            and p.occurrence_count >= self.min_occurrence_threshold
        ]
        
        return sorted(filtered_patterns, key=lambda x: x.confidence, reverse=True)
    
    def _detect_temporal_patterns(
        self, 
        interactions: List[Dict]
    ) -> List[Pattern]:
        """Detecta patrones temporales (horarios, días, frecuencias)."""
        patterns = []
        
        # Agrupar por hora del día
        hourly_dist = defaultdict(list)
        for interaction in interactions:
            if 'timestamp' in interaction:
                dt = datetime.fromisoformat(interaction['timestamp'])
                hourly_dist[dt.hour].append(dt)
        
        # Detectar horas pico
        peak_hours = sorted(
            [(hour, len(times)) for hour, times in hourly_dist.items()],
            key=lambda x: x[1],
            reverse=True
        )[:3]
        
        if peak_hours and peak_hours[0][1] >= 3:
            patterns.append(Pattern(
                name="peak_activity_hours",
                frequency=peak_hours[0][1] / len(interactions),
                confidence=min(0.9, 0.5 + (peak_hours[0][1] * 0.1)),
                trigger_conditions={
                    "type": "time_based",
                    "hours": [h[0] for h in peak_hours],
                    "priority": "high"
                },
                predicted_outcome="Usuario más receptivo a insights entre {}h".format(
                    ", ".join(map(str, [h[0] for h in peak_hours[:2]]))
                ),
                last_observed=datetime.now(),
                occurrence_count=peak_hours[0][1]
            ))
        
        return patterns
    
    def _detect_content_patterns(
        self, 
        interactions: List[Dict]
    ) -> List[Pattern]:
        """Detecta patrones en el tipo de contenido consumido."""
        patterns = []
        content_types = defaultdict(int)
        topics = defaultdict(int)
        
        for interaction in interactions:
            if 'content_type' in interaction:
                content_types[interaction['content_type']] += 1
            if 'topics' in interaction:
                for topic in interaction.get('topics', []):
                    topics[topic] += 1
        
        # Temas más frecuentes
        top_topics = sorted(topics.items(), key=lambda x: x[1], reverse=True)[:5]
        if top_topics and top_topics[0][1] >= 3:
            patterns.append(Pattern(
                name="content_interest_focus",
                frequency=top_topics[0][1] / len(interactions),
                confidence=min(0.9, 0.5 + (top_topics[0][1] * 0.1)),
                trigger_conditions={
                    "type": "content_based",
                    "topics": [t[0] for t in top_topics[:3]],
                    "min_engagement": "high"
                },
                predicted_outcome="Interés consistente en: {}".format(
                    ", ".join([t[0] for t in top_topics[:3]])
                ),
                last_observed=datetime.now(),
                occurrence_count=top_topics[0][1]
            ))
        
        return patterns
    
    def _detect_query_patterns(
        self, 
        interactions: List[Dict]
    ) -> List[Pattern]:
        """Detecta patrones en las consultas realizadas."""
        patterns = []
        query_templates = defaultdict(int)
        
        for interaction in interactions:
            if 'query_type' in interaction:
                query_templates[interaction['query_type']] += 1
        
        # Patrones de tipos de consulta
        for query_type, count in query_templates.items():
            if count >= 3:
                patterns.append(Pattern(
                    name=f"query_pattern_{query_type}",
                    frequency=count / len(interactions),
                    confidence=min(0.85, 0.5 + (count * 0.1)),
                    trigger_conditions={
                        "type": "query_based",
                        "query_type": query_type,
                        "frequency": "recurring"
                    },
                    predicted_outcome=f"Consultas frecuentes de tipo: {query_type}",
                    last_observed=datetime.now(),
                    occurrence_count=count
                ))
        
        return patterns
```

### 2.2 Prediction Engine (Motor de Predicciones)

```python
# core/anticipation/prediction_engine.py

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import numpy as np
from collections import defaultdict

class PredictionType(Enum):
    NEXT_NEED = "next_need"
    INFORMATION_GAP = "information_gap"
    PROJECT_RISK = "project_risk"
    OPPORTUNITY = "opportunity"
    DEADLINE_APPROACHING = "deadline_approaching"
    CONTEXT_SWITCH = "context_switch"

@dataclass
class Prediction:
    """Representa una predicción del sistema."""
    id: str
    prediction_type: PredictionType
    title: str
    description: str
    confidence: float
    urgency: float  # 0-1, qué pronto necesita atención
    recommended_action: str
    supporting_evidence: List[str]
    generated_at: datetime
    expires_at: Optional[datetime]
    metadata: Dict[str, Any] = None

class PredictionEngine:
    """
    Motor que genera predicciones basadas en patrones detectados
    y contexto del usuario.
    """
    
    def __init__(self, pattern_engine, memory_manager, graph_db):
        self.pattern_engine = pattern_engine
        self.memory = memory_manager
        self.graph = graph_db
        self.prediction_cache = {}
    
    async def generate_predictions(
        self,
        user_id: str,
        current_context: Dict[str, Any],
        time_horizon_hours: int = 24
    ) -> List[Prediction]:
        """
        Genera predicciones anticipatorias para el usuario.
        
        Args:
            user_id: Identificador del usuario
            current_context: Contexto actual del usuario
            time_horizon_hours: Horizonte temporal de predicciones
            
        Returns:
            Lista de predicciones ordenadas por urgencia
        """
        predictions = []
        
        # 1. Obtener patrones del usuario
        patterns = await self.pattern_engine.get_user_patterns(user_id)
        
        # 2. Generar predicciones de diferentes tipos
        predictions.extend(
            await self._predict_next_needs(user_id, patterns, current_context)
        )
        predictions.extend(
            await self._predict_information_gaps(user_id, patterns, current_context)
        )
        predictions.extend(
            await self._predict_deadlines(user_id, current_context)
        )
        predictions.extend(
            await self._predict_opportunities(user_id, patterns, current_context)
        )
        
        # 3. Filtrar por relevancia temporal
        now = datetime.now()
        relevant_predictions = [
            p for p in predictions 
            if p.urgency >= 0.5 or 
            (p.expires_at and p.expires_at > now)
        ]
        
        # 4. Ordenar por urgencia y confianza
        return sorted(
            relevant_predictions,
            key=lambda x: (x.urgency, x.confidence),
            reverse=True
        )
    
    async def _predict_next_needs(
        self,
        user_id: str,
        patterns: List[Any],
        context: Dict[str, Any]
    ) -> List[Prediction]:
        """Predice las próximas necesidades del usuario."""
        predictions = []
        
        # Analizar proyectos activos
        active_projects = context.get('active_projects', [])
        
        for project in active_projects:
            # Predecir necesidades basadas en tipo de proyecto
            project_type = project.get('type', 'general')
            
            need_predictions = {
                'development': [
                    "Necesitarás documentación de API pronto",
                    "Posible bug a investigar en el módulo X",
                    "Revisión de código pendiente"
                ],
                'research': [
                    "Fuentes adicionales necesarias para sección Y",
                    "Resumen ejecutivo所需的 insights",
                    "Verificación de datos faltante"
                ],
                'planning': [
                    "Próximos hitos a definir",
                    "Recursos a asignar",
                    "Stakeholders a consultar"
                ]
            }
            
            if project_type in need_predictions:
                predictions.append(Prediction(
                    id=f"need_{user_id}_{project['id']}_{datetime.now().timestamp()}",
                    prediction_type=PredictionType.NEXT_NEED,
                    title=f"Próxima necesidad: {project['name']}",
                    description=f"Basado en el progreso del proyecto, es probable que necesites:",
                    confidence=0.75,
                    urgency=0.6,
                    recommended_action=need_predictions[project_type][0],
                    supporting_evidence=[
                        f"Tipo de proyecto: {project_type}",
                        f"Patrones históricos detectados",
                        "Progreso actual del proyecto"
                    ],
                    generated_at=datetime.now(),
                    expires_at=datetime.now() + timedelta(hours=8),
                    metadata={'project_id': project['id']}
                ))
        
        return predictions
    
    async def _predict_information_gaps(
        self,
        user_id: str,
        patterns: List[Any],
        context: Dict[str, Any]
    ) -> List[Prediction]:
        """Predice brechas de información potenciales."""
        predictions = []
        
        # Analizar documentos recientes vs. temas consultados
        recent_queries = context.get('recent_queries', [])
        recent_docs = context.get('recent_documents', [])
        
        # Detectar temas consultados pero sin documentación
        consulted_topics = set(recent_queries)
        documented_topics = set(docs.get('topics', []) for docs in recent_docs)
        
        gaps = consulted_topics - documented_topics
        
        for gap_topic in list(gaps)[:3]:  # Limitar a 3 gaps
            predictions.append(Prediction(
                id=f"gap_{user_id}_{gap_topic}_{datetime.now().timestamp()}",
                prediction_type=PredictionType.INFORMATION_GAP,
                title=f"Brecha de información detectada: {gap_topic}",
                description=f"Has consultado '{gap_topic}' múltiples veces pero no tienes documentación guardada.",
                confidence=0.8,
                urgency=0.5,
                recommended_action=f"¿Quieres que guarde un resumen sobre '{gap_topic}'?",
                supporting_evidence=[
                    f"Consultas recientes sobre: {gap_topic}",
                    "No se encontró documentación relacionada",
                    "Patrón repetido en el historial"
                ],
                generated_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=24),
                metadata={'topic': gap_topic}
            ))
        
        return predictions
    
    async def _predict_deadlines(
        self,
        user_id: str,
        context: Dict[str, Any]
    ) -> List[Prediction]:
        """Predice deadlines aproximándose."""
        predictions = []
        
        tasks = context.get('tasks', [])
        now = datetime.now()
        
        for task in tasks:
            due_date = task.get('due_date')
            if due_date:
                due_dt = datetime.fromisoformat(due_date)
                hours_until_due = (due_dt - now).total_seconds() / 3600
                
                if 0 < hours_until_due <= 48:  # Deadline en las próximas 48h
                    urgency = 1.0 - (hours_until_due / 48)
                    
                    predictions.append(Prediction(
                        id=f"deadline_{user_id}_{task['id']}_{datetime.now().timestamp()}",
                        prediction_type=PredictionType.DEADLINE_APPROACHING,
                        title=f"Deadline aproximándose: {task['name']}",
                        description=f"'{task['name']}' vence en {int(hours_until_due)} horas.",
                        confidence=0.95,
                        urgency=urgency,
                        recommended_action="¿Te ayudo a priorizar o resumir lo que falta?",
                        supporting_evidence=[
                            f"Fecha de entrega: {due_date}",
                            "Tarea pendiente en tu lista",
                            "Tiempo restante: {} horas".format(int(hours_until_due))
                        ],
                        generated_at=datetime.now(),
                        expires_at=due_dt,
                        metadata={'task_id': task['id']}
                    ))
        
        return predictions
    
    async def _predict_opportunities(
        self,
        user_id: str,
        patterns: List[Any],
        context: Dict[str, Any]
    ) -> List[Prediction]:
        """Predice oportunidades basadas en patrones."""
        predictions = []
        
        # Analizar mejoras potenciales basadas en comportamiento
        for pattern in patterns:
            if pattern.name == "content_interest_focus":
                topics = pattern.trigger_conditions.get('topics', [])
                
                # Buscar conexiones con nuevos contenidos
                new_insights = await self._find_related_new_content(topics)
                
                for insight in new_insights[:2]:
                    predictions.append(Prediction(
                        id=f"opp_{user_id}_{insight['id']}_{datetime.now().timestamp()}",
                        prediction_type=PredictionType.OPPORTUNITY,
                        title=f"Nueva información sobre: {insight['topic']}",
                        description=insight['summary'],
                        confidence=insight.get('confidence', 0.7),
                        urgency=0.4,
                        recommended_action="¿Quieres ver más detalles sobre este tema?",
                        supporting_evidence=[
                            "Basado en tu interés en {}".format(", ".join(topics[:2])),
                            "Nuevo contenido disponible",
                            "Patrón de consumo de información"
                        ],
                        generated_at=datetime.now(),
                        expires_at=datetime.now() + timedelta(hours=48),
                        metadata={'topic': insight['topic']}
                    ))
        
        return predictions
    
    async def _find_related_new_content(
        self,
        topics: List[str]
    ) -> List[Dict[str, Any]]:
        """Busca nuevo contenido relacionado con los temas de interés."""
        # Implementación simplificada - en producción consultaría
        # fuentes externas, news APIs, etc.
        return []
```

### 2.3 Proactive Insight Generator (Generador de Insights Proactivos)

```python
# core/anticipation/insight_generator.py

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json

class InsightCategory(Enum):
    PATTERN_DISCOVERY = "pattern_discovery"
    CORRELATION = "correlation"
    TREND = "trend"
    RECOMMENDATION = "recommendation"
    WARNING = "warning"
    OPPORTUNITY = "opportunity"

@dataclass
class ProactiveInsight:
    """Representa un insight proactivo generado para el usuario."""
    id: str
    category: InsightCategory
    title: str
    description: str
    relevance_score: float  # 0-1, qué relevante es para el usuario
    action_items: List[str]
    related_data: Dict[str, Any]
    generated_at: datetime
    display_priority: int  # 1-10, menor es más prioritario
    expires_at: Optional[datetime]

class InsightGenerator:
    """
    Genera insights proactivos basándose en el análisis del
    contexto, patrones y predicciones del usuario.
    """
    
    def __init__(self, prediction_engine, graph_db, memory_manager):
        self.prediction_engine = prediction_engine
        self.graph = graph_db
        self.memory = memory_manager
        self.insight_templates = self._load_templates()
    
    def _load_templates(self) -> Dict[InsightCategory, Dict]:
        """Carga plantillas de insights."""
        return {
            InsightCategory.PATTERN_DISCOVERY: {
                "template": "He notado que {pattern_description}",
                "follow_up": "¿Te gustaría explorar esto más a fondo?"
            },
            InsightCategory.CORRELATION: {
                "template": "{entity_a} y {entity_b} están relacionados a través de {relationship}",
                "follow_up": "¿Quieres ver más conexiones?"
            },
            InsightCategory.TREND: {
                "template": "Hay una tendencia {direction} en {topic}: {change_percentage}%",
                "follow_up": "¿Te ayudo a profundizar en esta tendencia?"
            },
            InsightCategory.RECOMMENDATION: {
                "template": "Basado en {context}, te recomiendo {recommendation}",
                "follow_up": "¿Te gustaría que implemente esta recomendación?"
            },
            InsightCategory.WARNING: {
                "template": "Atención: {warning_condition}",
                "follow_up": "¿Qué acción quieres tomar?"
            }
        }
    
    async def generate_insights(
        self,
        user_id: str,
        current_context: Dict[str, Any],
        max_insights: int = 5
    ) -> List[ProactiveInsight]:
        """
        Genera insights proactivos para el usuario.
        
        Args:
            user_id: Identificador del usuario
            current_context: Contexto actual
            max_insights: Máximo número de insights a generar
            
        Returns:
            Lista de insights proactivos
        """
        insights = []
        
        # 1. Generar predicciones
        predictions = await self.prediction_engine.generate_predictions(
            user_id, current_context
        )
        
        # 2. Convertir predicciones a insights
        for prediction in predictions[:max_insights]:
            insight = await self._prediction_to_insight(prediction)
            if insight:
                insights.append(insight)
        
        # 3. Generar insights basados en grafo de conocimiento
        graph_insights = await self._generate_graph_insights(
            user_id, current_context
        )
        insights.extend(graph_insights)
        
        # 4. Generar insights basados en memoria
        memory_insights = await self._generate_memory_insights(
            user_id, current_context
        )
        insights.extend(memory_insights)
        
        # 5. Ordenar por prioridad
        sorted_insights = sorted(
            insights,
            key=lambda x: x.display_priority
        )[:max_insights]
        
        return sorted_insights
    
    async def _prediction_to_insight(
        self,
        prediction
    ) -> Optional[ProactiveInsight]:
        """Convierte una predicción en un insight proactivo."""
        
        category_map = {
            'next_need': InsightCategory.RECOMMENDATION,
            'information_gap': InsightCategory.WARNING,
            'deadline_approaching': InsightCategory.WARNING,
            'opportunity': InsightCategory.OPPORTUNITY
        }
        
        category = category_map.get(
            prediction.prediction_type.value,
            InsightCategory.RECOMMENDATION
        )
        
        return ProactiveInsight(
            id=f"insight_{prediction.id}",
            category=category,
            title=prediction.title,
            description=prediction.description,
            relevance_score=prediction.confidence,
            action_items=[prediction.recommended_action],
            related_data={'prediction': prediction.metadata},
            generated_at=datetime.now(),
            display_priority=int(prediction.urgency * 10),
            expires_at=prediction.expires_at
        )
    
    async def _generate_graph_insights(
        self,
        user_id: str,
        context: Dict[str, Any]
    ) -> List[ProactiveInsight]:
        """Genera insights basados en el grafo de conocimiento."""
        insights = []
        
        # Obtener entidades relacionadas con el contexto actual
        current_entities = context.get('current_entities', [])
        
        for entity in current_entities:
            # Buscar entidades relacionadas no exploradas
            related = await self.graph.find_related_entities(
                entity['id'],
                max_depth=2
            )
            
            unexplored = [
                r for r in related 
                if not r.get('explored', False)
            ]
            
            if unexplored:
                # Crear insight sobre conexión no explorada
                insights.append(ProactiveInsight(
                    id=f"graph_insight_{entity['id']}_{datetime.now().timestamp()}",
                    category=InsightCategory.CORRELATION,
                    title=f"Nueva conexión descubierta: {entity['name']}",
                    description=f"{entity['name']} está conectado con {len(unexplored)} conceptos relacionados que aún no has explorado.",
                    relevance_score=0.75,
                    action_items=[
                        "Ver conexiones relacionadas",
                        "Explorar {} en profundidad".format(entity['name']),
                        "Ignorar por ahora"
                    ],
                    related_data={
                        'entity': entity,
                        'related_entities': [r['name'] for r in unexplored[:3]]
                    },
                    generated_at=datetime.now(),
                    display_priority=7,
                    expires_at=datetime.now() + timedelta(hours=24)
                ))
        
        return insights
    
    async def _generate_memory_insights(
        self,
        user_id: str,
        context: Dict[str, Any]
    ) -> List[ProactiveInsight]:
        """Genera insights basados en la memoria del usuario."""
        insights = []
        
        # Obtener memorias recientes
        recent_memories = await self.memory.get_recent_memories(
            user_id,
            limit=20,
            time_window=timedelta(days=7)
        )
        
        if len(recent_memories) < 3:
            return insights
        
        # Analizar evolución temporal
        topics_by_week = defaultdict(list)
        for memory in recent_memories:
            week = memory['created_at'].isocalendar()[1]
            if 'topics' in memory:
                topics_by_week[week].extend(memory['topics'])
        
        if len(topics_by_week) >= 2:
            weeks = sorted(topics_by_week.keys())
            if len(weeks) >= 2:
                current_week_topics = set(topics_by_week[weeks[-1]])
                previous_week_topics = set(topics_by_week[weeks[-2]])
                
                new_topics = current_week_topics - previous_week_topics
                
                if new_topics:
                    insights.append(ProactiveInsight(
                        id=f"memory_insight_trend_{user_id}_{datetime.now().timestamp()}",
                        category=InsightCategory.TREND,
                        title="Evolución de intereses detectada",
                        description=f"Has comenzado a explorar nuevos temas: {', '.join(list(new_topics)[:3])}",
                        relevance_score=0.8,
                        action_items=[
                            "Profundizar en estos nuevos temas",
                            "Ver historial completo",
                            "Guardar como área de enfoque"
                        ],
                        related_data={
                            'new_topics': list(new_topics),
                            'previous_focus': list(previous_week_topics & current_week_topics)
                        },
                        generated_at=datetime.now(),
                        display_priority=6,
                        expires_at=datetime.now() + timedelta(hours=48)
                    ))
        
        return insights
    
    def format_insight_for_display(self, insight: ProactiveInsight) -> Dict[str, Any]:
        """Formatea un insight para mostrarlo en la UI."""
        return {
            'id': insight.id,
            'icon': self._get_icon_for_category(insight.category),
            'title': insight.title,
            'description': insight.description,
            'actions': insight.action_items,
            'priority': insight.display_priority,
            'timeAgo': self._format_time_ago(insight.generated_at)
        }
    
    def _get_icon_for_category(self, category: InsightCategory) -> str:
        """Retorna un icono para cada categoría de insight."""
        icons = {
            InsightCategory.PATTERN_DISCOVERY: '🔍',
            InsightCategory.CORRELATION: '🔗',
            InsightCategory.TREND: '📈',
            InsightCategory.RECOMMENDATION: '💡',
            InsightCategory.WARNING: '⚠️',
            InsightCategory.OPPORTUNITY: '✨'
        }
        return icons.get(category, '📌')
    
    def _format_time_ago(self, dt: datetime) -> str:
        """Formatea un datetime como 'hace X tiempo'."""
        now = datetime.now()
        delta = now - dt
        
        if delta.total_seconds() < 60:
            return "ahora mismo"
        elif delta.total_seconds() < 3600:
            mins = int(delta.total_seconds() / 60)
            return f"hace {mins} minuto(s)"
        elif delta.total_seconds() < 86400:
            hours = int(delta.total_seconds() / 3600)
            return f"hace {hours} hora(s)"
        else:
            days = int(delta.total_seconds() / 86400)
            return f"hace {days} día(s)"
```

### 2.4 Anticipation Scheduler (Planificador de Tareas Anticipatorias)

```python
# core/anticipation/anticipation_scheduler.py

from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import asyncio
from croniter import croniter

class TriggerType(Enum):
    TIME_BASED = "time_based"      # Cron schedule
    EVENT_BASED = "event_based"    # On specific events
    CONTEXT_BASED = "context_based" # When context changes
    PREDICTIVE = "predictive"       # Based on predictions

@dataclass
class AnticipationTask:
    """Tarea anticipatoria programada."""
    id: str
    name: str
    trigger_type: TriggerType
    trigger_config: Dict[str, Any]  # Configuración del trigger
    generator_function: str  # Nombre de la función a ejecutar
    parameters: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    user_id: Optional[str] = None  # None = sistema-wide

class AnticipationScheduler:
    """
    Planificador de tareas anticipatorias que ejecuta acciones
    proactivas según diferentes triggers.
    """
    
    def __init__(self, insight_generator, prediction_engine):
        self.insight_generator = insight_generator
        self.prediction_engine = prediction_engine
        self.tasks: Dict[str, AnticipationTask] = {}
        self.task_handlers: Dict[str, Callable] = {}
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """Registra los handlers por defecto."""
        self.task_handlers['generate_daily_insights'] = self._generate_daily_insights
        self.task_handlers['check_deadlines'] = self._check_deadlines
        self.task_handlers['update_predictions'] = self._update_predictions
        self.task_handlers['generate_weekly_report'] = self._generate_weekly_report
    
    def schedule_task(self, task: AnticipationTask):
        """Programa una nueva tarea anticipatoria."""
        self.tasks[task.id] = task
        
        if task.trigger_type == TriggerType.TIME_BASED:
            self._calculate_next_run(task)
    
    async def execute_pending_tasks(self):
        """Ejecuta todas las tareas pendientes."""
        now = datetime.now()
        
        for task_id, task in self.tasks.items():
            if not task.enabled:
                continue
            
            if task.next_run and task.next_run <= now:
                await self._execute_task(task)
                task.last_run = now
                self._calculate_next_run(task)
    
    async def _execute_task(self, task: AnticipationTask):
        """Ejecuta una tarea específica."""
        handler = self.task_handlers.get(task.generator_function)
        
        if handler:
            try:
                await handler(task)
            except Exception as e:
                # Log error
                print(f"Error executing task {task.id}: {e}")
    
    async def _generate_daily_insights(self, task: AnticipationTask):
        """Genera insights diarios para el usuario."""
        user_id = task.user_id
        if not user_id:
            return
        
        context = await self._get_user_context(user_id)
        insights = await self.insight_generator.generate_insights(
            user_id, context, max_insights=5
        )
        
        # Almacenar o enviar insights
        await self._deliver_insights(user_id, insights)
    
    async def _check_deadlines(self, task: AnticipationTask):
        """Verifica deadlines próximos."""
        user_id = task.user_id
        if not user_id:
            return
        
        context = await self._get_user_context(user_id)
        predictions = await self.prediction_engine.generate_predictions(
            user_id, context, time_horizon_hours=48
        )
        
        deadline_predictions = [
            p for p in predictions
            if p.prediction_type.value == 'deadline_approaching'
        ]
        
        if deadline_predictions:
            await self._notify_deadlines(user_id, deadline_predictions)
    
    async def _update_predictions(self, task: AnticipationTask):
        """Actualiza predicciones del modelo."""
        user_id = task.user_id
        if not user_id:
            return
        
        context = await self._get_user_context(user_id)
        await self.prediction_engine.generate_predictions(user_id, context)
    
    async def _generate_weekly_report(self, task: AnticipationTask):
        """Genera reporte semanal."""
        user_id = task.user_id
        if not user_id:
            return
        
        report = await self._compile_weekly_report(user_id)
        await self._deliver_report(user_id, report)
    
    def _calculate_next_run(self, task: AnticipationTask):
        """Calcula la próxima ejecución de una tarea."""
        if task.trigger_type == TriggerType.TIME_BASED:
            cron_expr = task.trigger_config.get('cron')
            if cron_expr:
                cron = croniter(cron_expr, datetime.now())
                task.next_run = cron.get_next(datetime)
    
    async def _get_user_context(self, user_id: str) -> Dict[str, Any]:
        """Obtiene el contexto actual del usuario."""
        # Implementar según la arquitectura existente
        return {}
    
    async def _deliver_insights(self, user_id: str, insights):
        """Entrega insights al usuario (WebSocket, notificación, etc."""
        # Implementar según el sistema de notificaciones existente
        pass
    
    async def _notify_deadlines(self, user_id: str, deadlines):
        """Notifica deadlines próximos."""
        pass
    
    async def _compile_weekly_report(self, user_id: str) -> Dict[str, Any]:
        """Compila el reporte semanal."""
        return {
            'period': 'última semana',
            'insights_generated': 0,
            'tasks_completed': 0,
            'topics_explored': []
        }
    
    async def _deliver_report(self, user_id: str, report):
        """Entrega el reporte semanal."""
        pass
```

## 3. Integración con el Agente Existente

```python
# core/enhanced_agent_with_anticipation.py

from core.agent import Agent
from core.anticipation.pattern_recognition import PatternRecognitionEngine
from core.anticipation.prediction_engine import PredictionEngine
from core.anticipation.insight_generator import InsightGenerator
from core.anticipation.anticipation_scheduler import AnticipationScheduler
from core.websocket_manager import send_personal_message

class AnticipatoryAgent(Agent):
    """
    Versión extendida del agente con capacidades anticipatorias.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Inicializar componentes anticipatorios
        self.pattern_engine = PatternRecognitionEngine(self.db)
        self.prediction_engine = PredictionEngine(
            self.pattern_engine, 
            self.memory_manager, 
            self.graph_db
        )
        self.insight_generator = InsightGenerator(
            self.prediction_engine,
            self.graph_db,
            self.memory_manager
        )
        self.scheduler = AnticipationScheduler(
            self.insight_generator,
            self.prediction_engine
        )
        
        # Tareas anticipatorias por defecto
        self._setup_default_anticipation_tasks()
    
    def _setup_default_anticipation_tasks(self):
        """Configura las tareas anticipatorias por defecto."""
        
        # Insights diarios
        self.scheduler.schedule_task(AnticipationTask(
            id="daily_insights_morning",
            name="Insights matutinos",
            trigger_type=TriggerType.TIME_BASED,
            trigger_config={'cron': '0 8 * * *'},  # 8 AM diario
            generator_function='generate_daily_insights',
            user_id=None  # Se asignará por usuario
        ))
        
        # Verificación de deadlines
        self.scheduler.schedule_task(AnticipationTask(
            id="deadline_check",
            name="Verificación de deadlines",
            trigger_type=TriggerType.TIME_BASED,
            trigger_config={'cron': '0 */4 * * *'},  # Cada 4 horas
            generator_function='check_deadlines'
        ))
    
    async def handle_user_message(
        self,
        message: str,
        user_id: str,
        account_id: str,
        include_anticipatory_insights: bool = True
    ) -> Dict[str, Any]:
        """
        Maneja un mensaje del usuario, opcionalmente incluyendo
        insights anticipatorios.
        """
        response = await super().handle_user_message(
            message, user_id, account_id
        )
        
        if include_anticipatory_insights:
            # Obtener contexto actual
            context = await self._get_current_context(user_id, account_id)
            
            # Generar insights anticipatorios
            insights = await self.insight_generator.generate_insights(
                user_id, context, max_insights=3
            )
            
            # Añadir insights a la respuesta
            response['anticipatory_insights'] = [
                self.insight_generator.format_insight_for_display(i)
                for i in insights
            ]
        
        return response
    
    async def get_proactive_insights(
        self,
        user_id: str,
        account_id: str
    ) -> List[Dict[str, Any]]:
        """
        Obtiene insights proactivos para mostrar al usuario.
        """
        context = await self._get_current_context(user_id, account_id)
        insights = await self.insight_generator.generate_insights(
            user_id, context, max_insights=5
        )
        
        return [
            self.insight_generator.format_insight_for_display(i)
            for i in insights
        ]
    
    async def _get_current_context(
        self,
        user_id: str,
        account_id: str
    ) -> Dict[str, Any]:
        """Obtiene el contexto actual del usuario."""
        return {
            'active_projects': await self._get_active_projects(account_id),
            'recent_queries': await self._get_recent_queries(user_id),
            'tasks': await self._get_pending_tasks(account_id),
            'current_entities': await self.graph_db.get_current_entities(account_id)
        }
    
    async def _get_active_projects(self, account_id: str) -> List[Dict]:
        """Obtiene proyectos activos del usuario."""
        # Implementar según la arquitectura existente
        return []
    
    async def _get_recent_queries(self, user_id: str) -> List[Dict]:
        """Obtiene consultas recientes del usuario."""
        # Implementar según la arquitectura existente
        return []
    
    async def _get_pending_tasks(self, account_id: str) -> List[Dict]:
        """Obtiene tareas pendientes."""
        # Implementar según la arquitectura existente
        return []
```

## 4. API para Acceder a Insights Anticipatorios

```python
# api/anticipation.py

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from pydantic import BaseModel

router = APIRouter(prefix="/anticipation", tags=["anticipation"])

class AnticipatoryInsightResponse(BaseModel):
    id: str
    icon: str
    title: str
    description: str
    actions: List[str]
    priority: int
    timeAgo: str

class InsightActionRequest(BaseModel):
    insight_id: str
    action: str  # "explore", "dismiss", "snooze"
    parameters: Optional[Dict] = None

@router.get("/insights/{user_id}", response_model=List[AnticipatoryInsightResponse])
async def get_user_insights(
    user_id: str,
    max_insights: int = 5
):
    """
    Obtiene los insights anticipatorios para un usuario.
    """
    agent = await get_anticipatory_agent()
    insights = await agent.get_proactive_insights(user_id, max_insights=max_insights)
    return insights

@router.post("/insights/{user_id}/action")
async def handle_insight_action(
    user_id: str,
    request: InsightActionRequest
):
    """
    Maneja la acción del usuario sobre un insight.
    """
    # Registrar la acción tomada
    await log_insight_action(user_id, request.insight_id, request.action)
    
    # Ejecutar la acción correspondiente
    if request.action == "explore":
        # Iniciar exploración del insight
        return {"status": "exploration_started", "insight_id": request.insight_id}
    elif request.action == "dismiss":
        # Marcar como descartado
        return {"status": "dismissed", "insight_id": request.insight_id}
    elif request.action == "snooze":
        # Posponer para más tarde
        snooze_until = request.parameters.get('until', 'tomorrow')
        return {"status": "snoozed", "insight_id": request.insight_id, "until": snooze_until}
    
    raise HTTPException(status_code=400, detail="Invalid action")

@router.get("/predictions/{user_id}")
async def get_user_predictions(user_id: str):
    """
    Obtiene predicciones para un usuario.
    """
    agent = await get_anticipatory_agent()
    context = await agent._get_current_context(user_id)
    predictions = await agent.prediction_engine.generate_predictions(
        user_id, context
    )
    return predictions

@router.post("/patterns/{user_id}/analyze")
async def analyze_user_patterns(user_id: str):
    """
    Fuerza el análisis de patrones del usuario.
    """
    agent = await get_anticipatory_agent()
    patterns = await agent.pattern_engine.analyze_user_behavior(
        user_id,
        await agent._get_recent_queries(user_id)
    )
    return {"patterns": [p.__dict__ for p in patterns]}
```

## 5. Ejemplo de Flujo de Uso

```python
# Ejemplo de uso del sistema anticipatorio

async def ejemplo_uso():
    """
    Ejemplo del flujo completo del sistema anticipatorio.
    """
    
    # 1. Inicializar componentes
    agent = await get_anticipatory_agent()
    
    # 2. El usuario interactúa normalmente
    response = await agent.handle_user_message(
        "¿Qué tareas tengo pendientes?",
        user_id="user_123",
        account_id="acc_456",
        include_anticipatory_insights=True
    )
    
    # 3. La respuesta incluye insights proactivos
    print("Respuesta:", response['message'])
    print("Insights Anticipatorios:")
    for insight in response.get('anticipatory_insights', []):
        print(f"  [{insight['icon']}] {insight['title']}")
        print(f"    {insight['description']}")
        print(f"    Acciones: {', '.join(insight['actions'])}")
    
    # 4. El usuario puede ver todos los insights
    all_insights = await agent.get_proactive_insights("user_123", "acc_456")
    
    # 5. El sistema ejecuta tareas programadas
    await agent.scheduler.execute_pending_tasks()
    
    # 6. El usuario puede tomar acciones sobre insights
    # (a través de la API o interfaz)
```

## 6. Métricas y Monitoreo

```python
# core/anticipation/metrics.py

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List

@dataclass
class AnticipationMetrics:
    """Métricas del sistema anticipatorio."""
    total_insights_generated: int = 0
    insights_acted_upon: int = 0
    insights_dismissed: int = 0
    prediction_accuracy: float = 0.0
    average_response_time_ms: float = 0.0
    user_engagement_score: float = 0.0

class MetricsCollector:
    """Recolector de métricas del sistema anticipatorio."""
    
    def __init__(self):
        self.metrics = AnticipationMetrics()
        self.insight_interactions = []
    
    def record_insight_generated(self, insight_id: str, category: str):
        """Registra un insight generado."""
        self.metrics.total_insights_generated += 1
        self.insight_interactions.append({
            'insight_id': insight_id,
            'category': category,
            'action': 'generated',
            'timestamp': datetime.now()
        })
    
    def record_insight_action(
        self,
        insight_id: str,
        action: str,
        time_to_action: float = None
    ):
        """Registra una acción sobre un insight."""
        if action == 'acted_upon':
            self.metrics.insights_acted_upon += 1
        elif action == 'dismissed':
            self.metrics.insights_dismissed += 1
        
        self.insight_interactions.append({
            'insight_id': insight_id,
            'action': action,
            'time_to_action': time_to_action,
            'timestamp': datetime.now()
        })
    
    def get_engagement_score(self) -> float:
        """Calcula el score de engagement."""
        total = self.metrics.insights_acted_upon + self.metrics.insights_dismissed
        if total == 0:
            return 0.0
        
        return self.metrics.insights_acted_upon / total
    
    def get_report(self) -> Dict[str, Any]:
        """Genera un reporte de métricas."""
        return {
            'total_insights': self.metrics.total_insights_generated,
            'acted_upon': self.metrics.insights_acted_upon,
            'dismissed': self.metrics.insights_dismissed,
            'engagement_rate': self.get_engagement_score(),
            'interactions': self.insight_interactions[-100:]  # Últimas 100 interacciones
        }
```

## Resumen

El sistema anticipatorio se compone de:

1. **Pattern Recognition Engine**: Detecta patrones en el comportamiento del usuario
2. **Prediction Engine**: Genera predicciones basadas en patrones y contexto
3. **Insight Generator**: Convierte predicciones en insights accionables
4. **Scheduler**: Ejecuta tareas proactivas según schedules configurados
5. **Metrics Collector**: Monitorea la efectividad del sistema

### Beneficios Principales

- **Respuestas proactivas** en lugar de solo reactivas
- **Personalización avanzada** basada en comportamiento histórico
- **Detección temprana** de oportunidades y riesgos
- **Mejora continua** mediante métricas de engagement
