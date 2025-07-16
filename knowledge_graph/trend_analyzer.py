"""
Analizador de Tendencias para detectar patrones temporales en el grafo de conocimiento.
Implementa detección de tendencias emergentes usando análisis temporal de conceptos.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from collections import defaultdict, Counter
import re

logger = logging.getLogger(__name__)

class TrendAnalyzer:
    """
    Analizador que detecta tendencias emergentes en el grafo de conocimiento.
    
    Características:
    - Análisis temporal de conceptos y entidades
    - Detección de tendencias emergentes
    - Análisis de evolución de temas
    - Predicción de tendencias futuras
    """
    
    def __init__(self, graph_db=None, sentence_transformer=None):
        """
        Inicializa el analizador de tendencias.
        
        Args:
            graph_db: Instancia de GraphDB
            sentence_transformer: Modelo para embeddings semánticos
        """
        self.graph_db = graph_db
        self.sentence_transformer = sentence_transformer
        self.trend_cache = {}
        logger.info("📈 TrendAnalyzer inicializado")
    
    async def detect_trends(
        self, 
        dataset_name: str,
        time_window: str = "last_6_months",
        trend_threshold: float = 0.7,
        granularity: str = "weekly"
    ) -> Dict[str, Any]:
        """
        Detecta tendencias emergentes en el dataset.
        
        Args:
            dataset_name: Nombre del dataset
            time_window: Ventana temporal (ej: "last_6_months", "last_1_year")
            trend_threshold: Umbral para considerar una tendencia (0.0-1.0)
            granularity: Granularidad temporal ("daily", "weekly", "monthly")
            
        Returns:
            Dict con tendencias detectadas
        """
        try:
            logger.info(f"📈 Detectando tendencias en '{dataset_name}' para {time_window}")
            
            # 1. Obtener datos temporales del grafo
            temporal_data = await self._get_temporal_data(dataset_name, time_window)
            
            if not temporal_data:
                logger.warning("⚠️ No se encontraron datos temporales")
                return {"trends": [], "message": "No hay datos temporales suficientes"}
            
            # 2. Analizar evolución de conceptos
            concept_evolution = await self._analyze_concept_evolution(
                temporal_data, granularity
            )
            
            # 3. Detectar tendencias emergentes
            emerging_trends = await self._detect_emerging_trends(
                concept_evolution, trend_threshold
            )
            
            # 4. Analizar tendencias de relaciones
            relationship_trends = await self._analyze_relationship_trends(
                temporal_data, granularity, trend_threshold
            )
            
            # 5. Calcular métricas de tendencias
            trend_metrics = await self._calculate_trend_metrics(
                emerging_trends, relationship_trends
            )
            
            # 6. Generar predicciones
            predictions = await self._generate_trend_predictions(
                concept_evolution, emerging_trends
            )
            
            result = {
                "dataset_name": dataset_name,
                "time_window": time_window,
                "granularity": granularity,
                "trend_threshold": trend_threshold,
                "analysis_timestamp": datetime.now().isoformat(),
                "emerging_trends": emerging_trends,
                "relationship_trends": relationship_trends,
                "trend_metrics": trend_metrics,
                "predictions": predictions,
                "summary": self._generate_trend_summary(emerging_trends, relationship_trends)
            }
            
            # Cachear resultados
            cache_key = f"{dataset_name}_{time_window}_{granularity}"
            self.trend_cache[cache_key] = result
            
            logger.info(f"✅ Detectadas {len(emerging_trends)} tendencias emergentes")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error detectando tendencias: {e}")
            raise
    
    async def _get_temporal_data(self, dataset_name: str, time_window: str) -> List[Dict[str, Any]]:
        """Obtiene datos temporales del grafo de conocimiento."""
        
        # Calcular fecha de inicio basada en time_window
        end_date = datetime.now()
        start_date = self._parse_time_window(time_window, end_date)
        
        # Query para obtener nodos con información temporal
        query = """
        MATCH (n)
        WHERE n.created_at IS NOT NULL
        AND datetime(n.created_at) >= datetime($start_date)
        AND datetime(n.created_at) <= datetime($end_date)
        RETURN n.id as id, n.name as name, n.type as type,
               n.created_at as created_at, n.confidence as confidence,
               n.source_document as source_document,
               n.category as category, n.concept as concept
        ORDER BY n.created_at
        """
        
        temporal_nodes = await self.graph_db.execute_query(query, {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        })
        
        # Query para obtener relaciones temporales
        rel_query = """
        MATCH (source)-[r]->(target)
        WHERE r.created_at IS NOT NULL
        AND datetime(r.created_at) >= datetime($start_date)
        AND datetime(r.created_at) <= datetime($end_date)
        RETURN source.id as source_id, target.id as target_id,
               type(r) as relationship_type, r.created_at as created_at,
               r.confidence as confidence, r.description as description
        ORDER BY r.created_at
        """
        
        temporal_relationships = await self.graph_db.execute_query(rel_query, {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        })
        
        return {
            "nodes": temporal_nodes,
            "relationships": temporal_relationships,
            "start_date": start_date,
            "end_date": end_date
        }
    
    def _parse_time_window(self, time_window: str, end_date: datetime) -> datetime:
        """Parsea la ventana temporal y calcula la fecha de inicio."""
        
        time_patterns = {
            r"last_(\d+)_days?": lambda x: end_date - timedelta(days=int(x)),
            r"last_(\d+)_weeks?": lambda x: end_date - timedelta(weeks=int(x)),
            r"last_(\d+)_months?": lambda x: end_date - timedelta(days=int(x) * 30),
            r"last_(\d+)_years?": lambda x: end_date - timedelta(days=int(x) * 365)
        }
        
        for pattern, calculator in time_patterns.items():
            match = re.match(pattern, time_window)
            if match:
                return calculator(match.group(1))
        
        # Fallback: últimos 6 meses
        return end_date - timedelta(days=180)
    
    async def _analyze_concept_evolution(
        self, 
        temporal_data: Dict[str, Any], 
        granularity: str
    ) -> Dict[str, Any]:
        """Analiza la evolución de conceptos en el tiempo."""
        
        nodes = temporal_data["nodes"]
        
        if not nodes:
            return {}
        
        # Convertir a DataFrame para análisis temporal
        df = pd.DataFrame(nodes)
        df['created_at'] = pd.to_datetime(df['created_at'])
        
        # Agrupar por período temporal
        if granularity == "daily":
            df['period'] = df['created_at'].dt.date
        elif granularity == "weekly":
            df['period'] = df['created_at'].dt.to_period('W')
        elif granularity == "monthly":
            df['period'] = df['created_at'].dt.to_period('M')
        else:
            df['period'] = df['created_at'].dt.date
        
        # Analizar evolución por tipo de entidad
        evolution_by_type = {}
        for entity_type in df['type'].unique():
            if pd.isna(entity_type):
                continue
                
            type_df = df[df['type'] == entity_type]
            type_evolution = type_df.groupby('period').agg({
                'id': 'count',
                'confidence': 'mean',
                'name': lambda x: list(x.unique())
            }).rename(columns={'id': 'count'})
            
            evolution_by_type[entity_type] = type_evolution.to_dict('index')
        
        # Analizar evolución por concepto
        evolution_by_concept = {}
        if 'concept' in df.columns:
            for concept in df['concept'].dropna().unique():
                concept_df = df[df['concept'] == concept]
                concept_evolution = concept_df.groupby('period').agg({
                    'id': 'count',
                    'confidence': 'mean'
                }).rename(columns={'id': 'count'})
                
                evolution_by_concept[concept] = concept_evolution.to_dict('index')
        
        return {
            "by_type": evolution_by_type,
            "by_concept": evolution_by_concept,
            "total_periods": len(df['period'].unique()),
            "date_range": {
                "start": df['created_at'].min().isoformat(),
                "end": df['created_at'].max().isoformat()
            }
        }
    
    async def _detect_emerging_trends(
        self, 
        concept_evolution: Dict[str, Any], 
        threshold: float
    ) -> List[Dict[str, Any]]:
        """Detecta tendencias emergentes basadas en la evolución de conceptos."""
        
        emerging_trends = []
        
        # Analizar tendencias por tipo
        for entity_type, evolution in concept_evolution.get("by_type", {}).items():
            trend = self._calculate_trend_score(evolution, "count")
            
            if trend["score"] >= threshold:
                emerging_trends.append({
                    "type": "entity_type_trend",
                    "entity_type": entity_type,
                    "trend_score": trend["score"],
                    "direction": trend["direction"],
                    "growth_rate": trend["growth_rate"],
                    "confidence": trend["confidence"],
                    "description": f"Tendencia {trend['direction']} en entidades de tipo '{entity_type}'"
                })
        
        # Analizar tendencias por concepto
        for concept, evolution in concept_evolution.get("by_concept", {}).items():
            trend = self._calculate_trend_score(evolution, "count")
            
            if trend["score"] >= threshold:
                emerging_trends.append({
                    "type": "concept_trend",
                    "concept": concept,
                    "trend_score": trend["score"],
                    "direction": trend["direction"],
                    "growth_rate": trend["growth_rate"],
                    "confidence": trend["confidence"],
                    "description": f"Tendencia {trend['direction']} en el concepto '{concept}'"
                })
        
        # Ordenar por puntuación de tendencia
        emerging_trends.sort(key=lambda x: x["trend_score"], reverse=True)
        
        return emerging_trends
    
    def _calculate_trend_score(self, evolution_data: Dict, metric: str) -> Dict[str, Any]:
        """Calcula la puntuación de tendencia para una serie temporal."""
        
        if not evolution_data:
            return {"score": 0, "direction": "stable", "growth_rate": 0, "confidence": 0}
        
        # Extraer valores de la métrica
        values = []
        periods = sorted(evolution_data.keys())
        
        for period in periods:
            period_data = evolution_data[period]
            if isinstance(period_data, dict) and metric in period_data:
                values.append(period_data[metric])
            else:
                values.append(0)
        
        if len(values) < 2:
            return {"score": 0, "direction": "stable", "growth_rate": 0, "confidence": 0}
        
        # Calcular tendencia usando regresión lineal simple
        x = np.arange(len(values))
        y = np.array(values)
        
        # Evitar división por cero
        if np.std(x) == 0:
            return {"score": 0, "direction": "stable", "growth_rate": 0, "confidence": 0}
        
        # Correlación de Pearson como indicador de tendencia
        correlation = np.corrcoef(x, y)[0, 1] if len(x) > 1 else 0
        
        # Calcular tasa de crecimiento
        if values[0] != 0:
            growth_rate = (values[-1] - values[0]) / values[0]
        else:
            growth_rate = 1.0 if values[-1] > 0 else 0.0
        
        # Determinar dirección
        if correlation > 0.1:
            direction = "creciente"
        elif correlation < -0.1:
            direction = "decreciente"
        else:
            direction = "estable"
        
        # Calcular confianza basada en consistencia
        confidence = abs(correlation) if not np.isnan(correlation) else 0
        
        # Puntuación final (combinación de correlación y magnitud)
        score = abs(correlation) * (1 + abs(growth_rate) * 0.5) if not np.isnan(correlation) else 0
        score = min(1.0, score)  # Normalizar a [0, 1]
        
        return {
            "score": round(score, 3),
            "direction": direction,
            "growth_rate": round(growth_rate, 3),
            "confidence": round(confidence, 3),
            "correlation": round(correlation, 3) if not np.isnan(correlation) else 0
        }
    
    async def _analyze_relationship_trends(
        self, 
        temporal_data: Dict[str, Any], 
        granularity: str, 
        threshold: float
    ) -> List[Dict[str, Any]]:
        """Analiza tendencias en las relaciones del grafo."""
        
        relationships = temporal_data["relationships"]
        
        if not relationships:
            return []
        
        # Convertir a DataFrame
        df = pd.DataFrame(relationships)
        df['created_at'] = pd.to_datetime(df['created_at'])
        
        # Agrupar por período
        if granularity == "daily":
            df['period'] = df['created_at'].dt.date
        elif granularity == "weekly":
            df['period'] = df['created_at'].dt.to_period('W')
        elif granularity == "monthly":
            df['period'] = df['created_at'].dt.to_period('M')
        
        # Analizar por tipo de relación
        relationship_trends = []
        
        for rel_type in df['relationship_type'].unique():
            if pd.isna(rel_type):
                continue
                
            type_df = df[df['relationship_type'] == rel_type]
            type_evolution = type_df.groupby('period').agg({
                'source_id': 'count',
                'confidence': 'mean'
            }).rename(columns={'source_id': 'count'})
            
            evolution_dict = type_evolution.to_dict('index')
            trend = self._calculate_trend_score(evolution_dict, "count")
            
            if trend["score"] >= threshold:
                relationship_trends.append({
                    "relationship_type": rel_type,
                    "trend_score": trend["score"],
                    "direction": trend["direction"],
                    "growth_rate": trend["growth_rate"],
                    "confidence": trend["confidence"],
                    "description": f"Tendencia {trend['direction']} en relaciones de tipo '{rel_type}'"
                })
        
        return relationship_trends
    
    async def _calculate_trend_metrics(
        self, 
        emerging_trends: List[Dict], 
        relationship_trends: List[Dict]
    ) -> Dict[str, Any]:
        """Calcula métricas generales de las tendencias."""
        
        all_trends = emerging_trends + relationship_trends
        
        if not all_trends:
            return {"total_trends": 0}
        
        trend_scores = [t["trend_score"] for t in all_trends]
        
        return {
            "total_trends": len(all_trends),
            "emerging_trends_count": len(emerging_trends),
            "relationship_trends_count": len(relationship_trends),
            "average_trend_score": round(np.mean(trend_scores), 3),
            "max_trend_score": round(max(trend_scores), 3),
            "trends_by_direction": {
                "creciente": len([t for t in all_trends if t["direction"] == "creciente"]),
                "decreciente": len([t for t in all_trends if t["direction"] == "decreciente"]),
                "estable": len([t for t in all_trends if t["direction"] == "estable"])
            }
        }
    
    async def _generate_trend_predictions(
        self, 
        concept_evolution: Dict, 
        emerging_trends: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Genera predicciones basadas en las tendencias detectadas."""
        
        predictions = []
        
        # Predicciones simples basadas en tendencias fuertes
        strong_trends = [t for t in emerging_trends if t["trend_score"] > 0.8]
        
        for trend in strong_trends:
            if trend["direction"] == "creciente":
                prediction = {
                    "type": "growth_prediction",
                    "subject": trend.get("concept") or trend.get("entity_type"),
                    "prediction": f"Se espera crecimiento continuo en los próximos períodos",
                    "confidence": trend["confidence"],
                    "timeframe": "next_month"
                }
                predictions.append(prediction)
        
        return predictions
    
    def _generate_trend_summary(
        self, 
        emerging_trends: List[Dict], 
        relationship_trends: List[Dict]
    ) -> Dict[str, Any]:
        """Genera un resumen de las tendencias detectadas."""
        
        total_trends = len(emerging_trends) + len(relationship_trends)
        
        if total_trends == 0:
            return {
                "message": "No se detectaron tendencias significativas",
                "recommendations": ["Aumentar el volumen de datos", "Reducir el umbral de tendencia"]
            }
        
        # Encontrar la tendencia más fuerte
        all_trends = emerging_trends + relationship_trends
        strongest_trend = max(all_trends, key=lambda x: x["trend_score"]) if all_trends else None
        
        return {
            "total_trends_detected": total_trends,
            "strongest_trend": strongest_trend,
            "trend_distribution": {
                "concept_trends": len([t for t in emerging_trends if t.get("type") == "concept_trend"]),
                "entity_type_trends": len([t for t in emerging_trends if t.get("type") == "entity_type_trend"]),
                "relationship_trends": len(relationship_trends)
            },
            "recommendations": self._generate_recommendations(all_trends)
        }
    
    def _generate_recommendations(self, trends: List[Dict]) -> List[str]:
        """Genera recomendaciones basadas en las tendencias."""
        
        recommendations = []
        
        growing_trends = [t for t in trends if t["direction"] == "creciente"]
        declining_trends = [t for t in trends if t["direction"] == "decreciente"]
        
        if growing_trends:
            recommendations.append(f"Explorar más a fondo {len(growing_trends)} tendencias crecientes detectadas")
        
        if declining_trends:
            recommendations.append(f"Investigar las causas de {len(declining_trends)} tendencias decrecientes")
        
        if len(trends) > 10:
            recommendations.append("Considerar filtrar tendencias por relevancia para enfocarse en las más importantes")
        
        return recommendations
