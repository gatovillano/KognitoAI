"""
Sistema de revisión y corrección de calidad de entidades en el grafo de conocimiento.
Identifica y corrige entidades mal clasificadas usando múltiples estrategias.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
import re
from datetime import datetime

logger = logging.getLogger(__name__)

class EntityQualityReviewer:
    """
    Revisor de calidad que identifica y corrige entidades mal clasificadas.
    
    Estrategias:
    1. Validación por patrones (regex)
    2. Validación contextual (LLM)
    3. Validación por listas conocidas
    4. Validación por frecuencia y co-ocurrencia
    """
    
    def __init__(self, graph_db=None, llm=None):
        """
        Inicializa el revisor de calidad.
        
        Args:
            graph_db: Instancia de GraphDB
            llm: Instancia del LLM para validación contextual
        """
        self.graph_db = graph_db
        self.llm = llm
        self.correction_stats = {
            "reviewed": 0,
            "corrected": 0,
            "deleted": 0,
            "merged": 0
        }
        
        # Patrones para validación
        self._init_validation_patterns()
        
        logger.info("✅ EntityQualityReviewer inicializado")
    
    def _init_validation_patterns(self):
        """Inicializa patrones de validación para diferentes tipos de entidades."""
        
        # Patrones que NO son organizaciones
        self.non_org_patterns = [
            r'^(el|la|los|las|un|una|unos|unas)\s+',  # Artículos
            r'^(de|del|en|con|por|para|desde|hasta)\s+',  # Preposiciones
            r'^\d+$',  # Solo números
            r'^[a-z]+$',  # Solo minúsculas (probablemente conceptos)
            r'^(año|años|día|días|mes|meses|hora|horas|minuto|minutos)$',  # Tiempo
            r'^(grande|pequeño|nuevo|viejo|bueno|malo|alto|bajo)$',  # Adjetivos
        ]
        
        # Patrones que NO son personas
        self.non_person_patterns = [
            r'^\d+$',  # Solo números
            r'^[A-Z]+$',  # Solo mayúsculas (probablemente siglas)
            r'^(sistema|proceso|método|técnica|tecnología|algoritmo)$',  # Conceptos técnicos
            r'^(año|años|día|días|mes|meses)$',  # Tiempo
            r'(\.com|\.org|\.net|\.edu|www\.)' # URLs/dominios
        ]
        
        # Patrones que NO son ubicaciones
        self.non_location_patterns = [
            r'^\d+$',  # Solo números
            r'^[a-z]+$',  # Solo minúsculas
            r'^(sistema|proceso|método|técnica|tecnología)$',  # Conceptos técnicos
            r'^(Dr\.|Prof\.|Sr\.|Sra\.).*',  # Títulos de personas
        ]
        
        # Palabras comunes que no son entidades
        self.common_non_entities = {
            'sistema', 'proceso', 'método', 'técnica', 'tecnología', 'algoritmo',
            'datos', 'información', 'análisis', 'estudio', 'investigación',
            'resultado', 'conclusión', 'objetivo', 'meta', 'propósito',
            'ejemplo', 'caso', 'situación', 'problema', 'solución',
            'año', 'años', 'día', 'días', 'mes', 'meses', 'hora', 'horas'
        }
    
    async def review_all_entities(self, workspace_id: Optional[str] = None, account_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Revisa todas las entidades en el grafo y sugiere correcciones.
        
        Args:
            workspace_id: ID del workspace (opcional)
            account_id: ID de la cuenta (obligatorio para aislamiento)
            
        Returns:
            Dict con estadísticas y sugerencias de corrección
        """
        try:
            logger.info(f"🔍 Iniciando revisión completa de entidades para cuenta: {account_id}...")
            
            # 1. Obtener todas las entidades
            entities = await self._get_all_entities(workspace_id, account_id)
            logger.info(f"📊 Revisando {len(entities)} entidades")
            
            # 2. Revisar cada tipo de entidad
            review_results = {
                "total_entities": len(entities),
                "corrections": [],
                "deletions": [],
                "merges": [],
                "statistics": {}
            }
            
            # Agrupar por tipo
            entities_by_type = {}
            for entity in entities:
                entity_type = entity.get("type", "UNKNOWN")
                if entity_type not in entities_by_type:
                    entities_by_type[entity_type] = []
                entities_by_type[entity_type].append(entity)
            
            # 3. Revisar cada tipo
            for entity_type, type_entities in entities_by_type.items():
                logger.info(f"🔍 Revisando {len(type_entities)} entidades de tipo {entity_type}")
                
                type_results = await self._review_entities_by_type(entity_type, type_entities)
                
                review_results["corrections"].extend(type_results["corrections"])
                review_results["deletions"].extend(type_results["deletions"])
                review_results["merges"].extend(type_results["merges"])
                review_results["statistics"][entity_type] = type_results["stats"]
            
            # 4. Generar resumen
            review_results["summary"] = self._generate_review_summary(review_results)
            
            logger.info(f"✅ Revisión completada: {len(review_results['corrections'])} correcciones sugeridas")
            
            return review_results
            
        except Exception as e:
            logger.error(f"❌ Error en revisión de entidades: {e}")
            raise
    
    async def _get_all_entities(self, workspace_id: Optional[str] = None, account_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Obtiene todas las entidades del grafo filtradas por usuario y workspace."""
        
        # Construir filtros de aislamiento
        where_clauses = []
        params = {}
        
        if account_id:
            where_clauses.append("n.account_id = $account_id")
            params["account_id"] = account_id
            
        if workspace_id:
            if workspace_id == "global_context" or not workspace_id:
                where_clauses.append("(n.workspace_id IS NULL OR n.workspace_id = '')")
            else:
                where_clauses.append("n.workspace_id = $workspace_id")
                params["workspace_id"] = workspace_id
        
        where_str = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        query = f"""
        MATCH (n)
        {where_str}
        RETURN n.id as id, n.name as name, n.type as type, 
               n.description as description, n.confidence as confidence,
               n.source as source, n.extraction_method as extraction_method,
               labels(n) as labels
        ORDER BY n.type, n.name
        """
        
        result = await self.graph_db.execute_query(query, params)
        return result
    
    async def _review_entities_by_type(self, entity_type: str, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Revisa entidades de un tipo específico."""
        
        results = {
            "corrections": [],
            "deletions": [],
            "merges": [],
            "stats": {
                "total": len(entities),
                "valid": 0,
                "invalid": 0,
                "duplicates": 0
            }
        }
        
        # 1. Validación por patrones
        for entity in entities:
            pattern_result = self._validate_entity_by_patterns(entity_type, entity)
            
            if pattern_result["action"] == "correct":
                results["corrections"].append(pattern_result)
                results["stats"]["invalid"] += 1
            elif pattern_result["action"] == "delete":
                results["deletions"].append(pattern_result)
                results["stats"]["invalid"] += 1
            else:
                results["stats"]["valid"] += 1
        
        # 2. Detectar duplicados
        duplicates = self._find_duplicate_entities(entities)
        for duplicate_group in duplicates:
            merge_suggestion = {
                "action": "merge",
                "entities": duplicate_group,
                "reason": "Entidades duplicadas o muy similares",
                "suggested_name": duplicate_group[0]["name"],  # Usar el primero como base
                "confidence": "high"
            }
            results["merges"].append(merge_suggestion)
            results["stats"]["duplicates"] += len(duplicate_group) - 1
        
        return results
    
    def _validate_entity_by_patterns(self, entity_type: str, entity: Dict[str, Any]) -> Dict[str, Any]:
        """Valida una entidad usando patrones regex."""
        
        # Asegurar que name sea un string, incluso si es None en Neo4j
        raw_name = entity.get("name")
        if raw_name is None:
            # Si no hay name, buscar en title o description como fallback para evitar descartar falsos negativos
            raw_name = entity.get("title") or entity.get("description") or ""
            
        name = str(raw_name).strip()
        
        # Validación básica
        if not name or len(name) < 2:
            return {
                "action": "delete",
                "entity": entity,
                "reason": "Nombre muy corto o vacío",
                "confidence": "high"
            }
        
        # Validar según el tipo
        if entity_type == "ORG":
            return self._validate_organization(entity)
        elif entity_type == "PER":
            return self._validate_person(entity)
        elif entity_type == "LOC":
            return self._validate_location(entity)
        else:
            return self._validate_generic_entity(entity)
    
    def _validate_organization(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """Valida si una entidad es realmente una organización."""
        
        name = str(entity.get("name") or "").strip().lower()
        
        # Verificar patrones que NO son organizaciones
        for pattern in self.non_org_patterns:
            if re.match(pattern, name, re.IGNORECASE):
                return {
                    "action": "correct",
                    "entity": entity,
                    "suggested_type": "CONCEPT",
                    "reason": f"No parece ser una organización: '{name}'",
                    "confidence": "high"
                }
        
        # Verificar palabras comunes
        if name in self.common_non_entities:
            return {
                "action": "correct",
                "entity": entity,
                "suggested_type": "CONCEPT",
                "reason": f"Palabra común, no organización: '{name}'",
                "confidence": "high"
            }
        
        return {"action": "keep", "entity": entity}
    
    def _validate_person(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """Valida si una entidad es realmente una persona."""
        
        name = str(entity.get("name") or "").strip().lower()
        
        # Verificar patrones que NO son personas
        for pattern in self.non_person_patterns:
            if re.match(pattern, name, re.IGNORECASE):
                return {
                    "action": "correct",
                    "entity": entity,
                    "suggested_type": "CONCEPT",
                    "reason": f"No parece ser una persona: '{name}'",
                    "confidence": "high"
                }
        
        # Verificar palabras comunes
        if name in self.common_non_entities:
            return {
                "action": "correct",
                "entity": entity,
                "suggested_type": "CONCEPT",
                "reason": f"Palabra común, no persona: '{name}'",
                "confidence": "high"
            }
        
        return {"action": "keep", "entity": entity}
    
    def _validate_location(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """Valida si una entidad es realmente una ubicación."""
        
        name = str(entity.get("name") or "").strip().lower()
        
        # Verificar patrones que NO son ubicaciones
        for pattern in self.non_location_patterns:
            if re.match(pattern, name, re.IGNORECASE):
                return {
                    "action": "correct",
                    "entity": entity,
                    "suggested_type": "CONCEPT",
                    "reason": f"No parece ser una ubicación: '{name}'",
                    "confidence": "high"
                }
        
        # Verificar palabras comunes
        if name in self.common_non_entities:
            return {
                "action": "correct",
                "entity": entity,
                "suggested_type": "CONCEPT",
                "reason": f"Palabra común, no ubicación: '{name}'",
                "confidence": "high"
            }
        
        return {"action": "keep", "entity": entity}
    
    def _validate_generic_entity(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """Validación genérica para otros tipos de entidades."""
        
        name = str(entity.get("name") or "").strip().lower()
        
        # Verificar si es muy corto
        if len(name) < 3:
            return {
                "action": "delete",
                "entity": entity,
                "reason": f"Nombre muy corto: '{name}'",
                "confidence": "medium"
            }
        
        return {"action": "keep", "entity": entity}
    
    def _find_duplicate_entities(self, entities: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Encuentra entidades duplicadas o muy similares."""
        
        duplicates = []
        processed = set()
        
        for i, entity1 in enumerate(entities):
            if i in processed:
                continue
                
            name1 = str(entity1.get("name") or "").strip().lower()
            duplicate_group = [entity1]
            
            for j, entity2 in enumerate(entities[i+1:], i+1):
                if j in processed:
                    continue
                    
                name2 = str(entity2.get("name") or "").strip().lower()
                
                # Verificar si son duplicados
                if self._are_duplicates(name1, name2):
                    duplicate_group.append(entity2)
                    processed.add(j)
            
            if len(duplicate_group) > 1:
                duplicates.append(duplicate_group)
                processed.add(i)
        
        return duplicates
    
    def _are_duplicates(self, name1: str, name2: str) -> bool:
        """Determina si dos nombres representan la misma entidad."""
        
        # Exactamente iguales
        if name1 == name2:
            return True
        
        # Uno contiene al otro
        if name1 in name2 or name2 in name1:
            return True
        
        # Similitud alta (implementación simple)
        # Podrías usar bibliotecas como difflib para algo más sofisticado
        words1 = set(name1.split())
        words2 = set(name2.split())
        
        if len(words1) > 0 and len(words2) > 0:
            intersection = words1.intersection(words2)
            union = words1.union(words2)
            similarity = len(intersection) / len(union)
            
            return similarity > 0.8
        
        return False
    
    def _generate_review_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Genera un resumen de la revisión."""
        
        total_corrections = len(results["corrections"])
        total_deletions = len(results["deletions"])
        total_merges = len(results["merges"])
        total_entities = results["total_entities"]
        
        return {
            "total_entities": total_entities,
            "issues_found": total_corrections + total_deletions + total_merges,
            "corrections_needed": total_corrections,
            "deletions_needed": total_deletions,
            "merges_needed": total_merges,
            "quality_score": max(0, 100 - ((total_corrections + total_deletions) / total_entities * 100)) if total_entities > 0 else 0,
            "recommendations": self._generate_recommendations(results)
        }
    
    def _generate_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Genera recomendaciones basadas en los resultados."""
        
        recommendations = []
        
        if len(results["corrections"]) > 0:
            recommendations.append(f"Corregir {len(results['corrections'])} entidades mal clasificadas")
        
        if len(results["deletions"]) > 0:
            recommendations.append(f"Eliminar {len(results['deletions'])} entidades inválidas")
        
        if len(results["merges"]) > 0:
            recommendations.append(f"Fusionar {len(results['merges'])} grupos de entidades duplicadas")
        
        # Análisis por tipo
        for entity_type, stats in results["statistics"].items():
            if stats["invalid"] > stats["valid"] * 0.3:  # Más del 30% inválidas
                recommendations.append(f"Revisar extracción de entidades tipo {entity_type} (alta tasa de error)")
        
        return recommendations

    async def apply_corrections(self, corrections: List[Dict[str, Any]], auto_apply: bool = False, account_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Aplica las correcciones sugeridas al grafo.

        Args:
            corrections: Lista de correcciones a aplicar
            auto_apply: Si aplicar automáticamente sin confirmación
            account_id: ID de la cuenta para validación de propiedad

        Returns:
            Dict con resultados de la aplicación
        """
        try:
            logger.info(f"🔧 Aplicando {len(corrections)} correcciones para cuenta: {account_id}...")

            results = {
                "applied": 0,
                "failed": 0,
                "skipped": 0,
                "details": []
            }

            for correction in corrections:
                try:
                    action = correction.get("action")

                    if action == "correct":
                        success = await self._apply_type_correction(correction, account_id)
                    elif action == "delete":
                        success = await self._apply_deletion(correction, account_id)
                    elif action == "merge":
                        success = await self._apply_merge(correction, account_id)
                    else:
                        success = False
                        logger.warning(f"⚠️ Acción desconocida: {action}")

                    if success:
                        results["applied"] += 1
                        results["details"].append({
                            "action": action,
                            "status": "success",
                            "entity": correction.get("entity", {}).get("name", "unknown")
                        })
                    else:
                        results["failed"] += 1
                        results["details"].append({
                            "action": action,
                            "status": "failed",
                            "entity": correction.get("entity", {}).get("name", "unknown")
                        })

                except Exception as e:
                    logger.error(f"❌ Error aplicando corrección: {e}")
                    results["failed"] += 1

            logger.info(f"✅ Correcciones aplicadas: {results['applied']} exitosas, {results['failed']} fallidas")

            return results

        except Exception as e:
            logger.error(f"❌ Error aplicando correcciones: {e}")
            raise

    async def _apply_type_correction(self, correction: Dict[str, Any], account_id: Optional[str] = None) -> bool:
        """Aplica una corrección de tipo de entidad."""

        try:
            entity = correction["entity"]
            new_type = correction["suggested_type"]
            entity_id = entity.get("id")

            if not entity_id:
                return False

            # Query para cambiar el tipo y label, filtrando por account_id
            query = f"""
            MATCH (n {{id: $entity_id}})
            WHERE n.account_id = $account_id
            REMOVE n:`{entity.get("type", "Entity")}`
            SET n:`{new_type}`
            SET n.type = $new_type
            SET n.corrected_at = $timestamp
            SET n.correction_reason = $reason
            RETURN n.name as name
            """

            result = await self.graph_db.execute_query(query, {
                "entity_id": entity_id,
                "account_id": account_id,
                "new_type": new_type,
                "timestamp": datetime.now().isoformat(),
                "reason": correction.get("reason", "")
            })

            return len(result) > 0

        except Exception as e:
            logger.error(f"❌ Error corrigiendo tipo de entidad: {e}")
            return False

    async def _apply_deletion(self, correction: Dict[str, Any], account_id: Optional[str] = None) -> bool:
        """Aplica una eliminación de entidad."""

        try:
            entity = correction["entity"]
            entity_id = entity.get("id")

            if not entity_id:
                return False

            # Query para eliminar la entidad y sus relaciones, filtrando por account_id
            query = """
            MATCH (n {id: $entity_id})
            WHERE n.account_id = $account_id
            DETACH DELETE n
            """

            await self.graph_db.execute_query(query, {"entity_id": entity_id, "account_id": account_id})

            return True

        except Exception as e:
            logger.error(f"❌ Error eliminando entidad: {e}")
            return False

    async def _apply_merge(self, correction: Dict[str, Any], account_id: Optional[str] = None) -> bool:
        """Aplica una fusión de entidades duplicadas."""

        try:
            entities = correction["entities"]
            if len(entities) < 2:
                return False

            # Usar la primera entidad como base
            main_entity = entities[0]
            duplicate_entities = entities[1:]

            main_id = main_entity.get("id")
            if not main_id:
                return False

            # Fusionar relaciones de las entidades duplicadas a la principal
            for duplicate in duplicate_entities:
                duplicate_id = duplicate.get("id")
                if not duplicate_id:
                    continue

                # Transferir relaciones entrantes
                await self.graph_db.execute_query("""
                    MATCH (source)-[r]->(duplicate {id: $duplicate_id})
                    MATCH (main {id: $main_id})
                    WHERE source.id <> $main_id 
                    AND duplicate.account_id = $account_id
                    AND main.account_id = $account_id
                    CREATE (source)-[new_r:MERGED_RELATION]->(main)
                    SET new_r = properties(r)
                    DELETE r
                """, {"duplicate_id": duplicate_id, "main_id": main_id, "account_id": account_id})

                # Transferir relaciones salientes
                await self.graph_db.execute_query("""
                    MATCH (duplicate {id: $duplicate_id})-[r]->(target)
                    MATCH (main {id: $main_id})
                    WHERE target.id <> $main_id
                    AND duplicate.account_id = $account_id
                    AND main.account_id = $account_id
                    CREATE (main)-[new_r:MERGED_RELATION]->(target)
                    SET new_r = properties(r)
                    DELETE r
                """, {"duplicate_id": duplicate_id, "main_id": main_id, "account_id": account_id})

                # Eliminar entidad duplicada
                await self.graph_db.execute_query("""
                    MATCH (n {id: $duplicate_id})
                    WHERE n.account_id = $account_id
                    DELETE n
                """, {"duplicate_id": duplicate_id, "account_id": account_id})

            # Marcar la entidad principal como fusionada
            await self.graph_db.execute_query("""
                MATCH (n {id: $main_id})
                WHERE n.account_id = $account_id
                SET n.merged_at = $timestamp
                SET n.merged_count = $count
            """, {
                "main_id": main_id,
                "account_id": account_id,
                "timestamp": datetime.now().isoformat(),
                "count": len(duplicate_entities)
            })

            return True

        except Exception as e:
            logger.error(f"❌ Error fusionando entidades: {e}")
            return False
