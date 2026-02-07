# knowledge_graph/output_parsers_graph.py

import logging
from typing import List, Dict, Any, Tuple
import uuid

from core.citation_models import Source, SourceType

logger = logging.getLogger(__name__)

class GraphOutputParser:
    """
    Parsea y formatea la salida cruda de una consulta Cypher para su uso en el agente.

    Transforma una lista de registros de Neo4j en:
    1.  Un contexto textual legible para el LLM.
    2.  Una lista de objetos `Source` para citaciones.
    """

    def parse(self, query_results: List[Dict[str, Any]]) -> Tuple[str, List[Source]]:
        """
        Punto de entrada principal para parsear los resultados.

        Args:
            query_results: La lista de diccionarios devuelta por GraphDB.execute_query.

        Returns:
            Una tupla conteniendo:
            - El contexto formateado como una cadena de texto.
            - Una lista de objetos Source para la citación.
        """
        if not query_results:
            return "No se encontraron resultados en el grafo de conocimiento.", []

        seen_nodes = set()
        seen_edges = set()
        text_parts = []
        sources = []

        for record in query_results:
            path = record.get("path")
            if path:
                # Si la consulta devuelve un path, lo procesamos
                path_dict = self._to_dict(path)
                nodes = path_dict.get('nodes', [])
                relationships = path_dict.get('relationships', [])

                for node in nodes:
                    node_id = node.get('id')
                    if node_id and node_id not in seen_nodes:
                        # Usar un ID numérico para la cita si es posible para consistencia
                        citation_id = len(sources) + 1
                        text, source = self._format_node(node, citation_id)
                        text_parts.append(text)
                        sources.append(source)
                        seen_nodes.add(node_id)

                for rel in relationships:
                    rel_id = rel.get('id')
                    if rel_id and rel_id not in seen_edges:
                        citation_id = len(sources) + 1
                        text, source = self._format_relationship(rel, nodes, citation_id)
                        text_parts.append(text)
                        # Las relaciones también pueden ser fuentes si queremos citarlas específicamente
                        # sources.append(source) 
                        seen_edges.add(rel_id)
            else:
                # Si la consulta devuelve nodos y relaciones por separado (n, r, m)
                for key, value in record.items():
                    # Convertir a dict si es un objeto de Neo4j
                    val_dict = self._to_dict(value)
                    
                    if isinstance(val_dict, dict): # Es un nodo o una relación
                        if 'start_node' in val_dict and 'end_node' in val_dict: # Es una relación
                             rel_id = val_dict.get('id')
                             if rel_id and rel_id not in seen_edges:
                                citation_id = len(sources) + 1
                                text, source = self._format_relationship(val_dict, [], citation_id)
                                text_parts.append(text)
                                seen_edges.add(rel_id)
                        else: # Es un nodo
                            node_id = val_dict.get('id')
                            if node_id and node_id not in seen_nodes:
                                citation_id = len(sources) + 1
                                text, source = self._format_node(val_dict, citation_id)
                                text_parts.append(text)
                                sources.append(source)
                                seen_nodes.add(node_id)

        formatted_context = "\n".join(text_parts)
        return formatted_context, sources

    def _to_dict(self, obj: Any) -> Any:
        """
        Convierte objetos de Neo4j (Node, Relationship, Path) a diccionarios estándar.
        """
        if isinstance(obj, dict) or obj is None:
            return obj
            
        # Caso: Path de Neo4j
        if hasattr(obj, "nodes") and hasattr(obj, "relationships"):
            return {
                'nodes': [self._to_dict(n) for n in obj.nodes],
                'relationships': [self._to_dict(r) for r in obj.relationships]
            }
            
        # Caso: Node de Neo4j
        if hasattr(obj, "labels"):
            # Convertir propiedades a dict
            d = dict(obj)
            # Asegurar que tenga 'id' y 'type'
            if 'id' not in d:
                # Prioridad: cognee_id property > element_id > id(n)
                d['id'] = d.get('cognee_id') or getattr(obj, 'element_id', None) or getattr(obj, 'id', None)
            if 'type' not in d:
                d['type'] = list(obj.labels)[0] if obj.labels else 'Entity'
            return d
            
        # Caso: Relationship de Neo4j
        if hasattr(obj, "start_node") and hasattr(obj, "end_node"):
            # Convertir propiedades a dict
            d = dict(obj)
            # Asegurar que tenga 'id', 'type', 'start_node' y 'end_node'
            if 'id' not in d:
                d['id'] = getattr(obj, 'element_id', None) or getattr(obj, 'id', None)
            if 'type' not in d:
                d['type'] = getattr(obj, 'type', 'RELATED')
            if 'start_node' not in d:
                # Intentar obtener el ID de la propiedad o el element_id del nodo
                start_node = obj.start_node
                d['start_node'] = start_node.get('id') or start_node.get('cognee_id') or getattr(start_node, 'element_id', None)
            if 'end_node' not in d:
                end_node = obj.end_node
                d['end_node'] = end_node.get('id') or end_node.get('cognee_id') or getattr(end_node, 'element_id', None)
            return d
            
        return obj

    def _format_node(self, node: Dict[str, Any], citation_id: int) -> Tuple[str, Source]:
        """Formatea un único nodo y crea su objeto Source, mostrando todas sus propiedades."""
        node_id = node.get('id', str(uuid.uuid4()))
        node_type = node.get('type', 'Desconocido')
        name = node.get('name', 'Sin nombre')
        description = node.get('description', '')
        
        text = f"**Nodo del Grafo [{citation_id}]:**\n"
        text += f"- **Tipo:** {node_type}\n"
        text += f"- **Nombre:** {name}\n"
        if description:
            text += f"- **Descripción:** {description}\n"
        
        # Propiedades adicionales que queremos mostrar explícitamente
        important_props = {
            'concept': 'Concepto',
            'category': 'Categoría',
            'confidence': 'Confianza',
            'source_document': 'Documento Fuente',
            'source': 'Fuente',
            'extraction_method': 'Método de Extracción',
            'created_at': 'Creado',
            'dataset_name': 'Dataset',
            'workspace_id': 'Workspace',
            'account_id': 'Cuenta'
        }
        
        # Mostrar propiedades importantes si existen
        for prop_key, prop_label in important_props.items():
            if prop_key in node and node[prop_key] is not None:
                value = node[prop_key]
                # Formatear valores especiales
                if prop_key == 'confidence' and isinstance(value, (int, float)):
                    value = f"{value:.2%}" if value <= 1 else f"{value:.2f}"
                text += f"- **{prop_label}:** {value}\n"
        
        # Mostrar otras propiedades no listadas (excluyendo las ya mostradas y las internas)
        excluded_keys = {'id', 'type', 'name', 'description'} | set(important_props.keys())
        other_props = {k: v for k, v in node.items() 
                      if k not in excluded_keys 
                      and v is not None 
                      and not k.startswith('_')}
        
        if other_props:
            text += "- **Propiedades Adicionales:**\n"
            for key, value in other_props.items():
                # Limitar el tamaño de valores muy largos
                str_value = str(value)
                if len(str_value) > 100:
                    str_value = str_value[:97] + "..."
                text += f"  - {key}: {str_value}\n"

        source = Source(
            id=citation_id,
            title=f"Nodo: {name}",
            snippet=description or name,
            type=SourceType.GRAPH,
            url=f"graph://node/{node_id}",
            metadata=node
        )
        return text, source

    def _format_relationship(self, rel: Dict[str, Any], nodes_in_path: List[Dict[str, Any]], citation_id: int) -> Tuple[str, Source]:
        """Formatea una única relación y crea su objeto Source, mostrando todas sus propiedades."""
        rel_id = rel.get('id', str(uuid.uuid4()))
        rel_type = rel.get('type', 'RELACIONADO_CON')
        start_node_id = rel.get('start_node')
        end_node_id = rel.get('end_node')

        # Buscar los nombres de los nodos en la lista de nodos del path
        start_node_name = self._find_node_name(start_node_id, nodes_in_path)
        end_node_name = self._find_node_name(end_node_id, nodes_in_path)

        text = f"**Relación del Grafo [{citation_id}]:**\n"
        text += f"- De '{start_node_name}' a '{end_node_name}'\n"
        text += f"- **Tipo:** {rel_type}\n"
        
        # Propiedades adicionales importantes de las relaciones
        important_rel_props = {
            'description': 'Descripción',
            'weight': 'Peso',
            'confidence': 'Confianza',
            'source': 'Fuente',
            'created_at': 'Creado',
            'dataset_name': 'Dataset'
        }
        
        # Mostrar propiedades importantes si existen
        for prop_key, prop_label in important_rel_props.items():
            if prop_key in rel and rel[prop_key] is not None:
                value = rel[prop_key]
                # Formatear valores especiales
                if prop_key in ['confidence', 'weight'] and isinstance(value, (int, float)):
                    value = f"{value:.2%}" if value <= 1 else f"{value:.2f}"
                text += f"- **{prop_label}:** {value}\n"
        
        # Mostrar otras propiedades no listadas
        excluded_keys = {'id', 'type', 'start_node', 'end_node'} | set(important_rel_props.keys())
        other_props = {k: v for k, v in rel.items() 
                      if k not in excluded_keys 
                      and v is not None 
                      and not k.startswith('_')}
        
        if other_props:
            text += "- **Propiedades Adicionales:**\n"
            for key, value in other_props.items():
                str_value = str(value)
                if len(str_value) > 100:
                    str_value = str_value[:97] + "..."
                text += f"  - {key}: {str_value}\n"

        source = Source(
            id=citation_id,
            title=f"Relación: {rel_type}",
            snippet=f"({start_node_name})-[{rel_type}]->({end_node_name})",
            type=SourceType.GRAPH,
            url=f"graph://relationship/{rel_id}",
            metadata=rel
        )
        return text, source

    def _find_node_name(self, node_id: str, nodes: List[Dict[str, Any]]) -> str:
        """Encuentra el nombre de un nodo en una lista por su ID."""
        for node in nodes:
            if node.get('id') == node_id:
                return node.get('name', f"ID: {node_id}")
        return f"ID: {node_id}"
