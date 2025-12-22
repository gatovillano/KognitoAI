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
                nodes = path.get('nodes', [])
                relationships = path.get('relationships', [])

                for node in nodes:
                    if node['id'] not in seen_nodes:
                        text, source = self._format_node(node)
                        text_parts.append(text)
                        sources.append(source)
                        seen_nodes.add(node['id'])

                for rel in relationships:
                    if rel['id'] not in seen_edges:
                        text, source = self._format_relationship(rel, nodes)
                        text_parts.append(text)
                        # Las relaciones también pueden ser fuentes
                        # sources.append(source) 
                        seen_edges.add(rel['id'])
            else:
                # Si la consulta devuelve nodos y relaciones por separado (n, r, m)
                for key, value in record.items():
                    if isinstance(value, dict): # Es un nodo o una relación
                        if 'start_node' in value and 'end_node' in value: # Es una relación
                             if value['id'] not in seen_edges:
                                text, source = self._format_relationship(value, [])
                                text_parts.append(text)
                                seen_edges.add(value['id'])
                        else: # Es un nodo
                            if value.get('id') and value['id'] not in seen_nodes:
                                text, source = self._format_node(value)
                                text_parts.append(text)
                                sources.append(source)
                                seen_nodes.add(value['id'])

        formatted_context = "\n".join(text_parts)
        return formatted_context, sources

    def _format_node(self, node: Dict[str, Any]) -> Tuple[str, Source]:
        """Formatea un único nodo y crea su objeto Source."""
        node_id = node.get('id', str(uuid.uuid4()))
        node_type = node.get('type', 'Desconocido')
        name = node.get('name', 'Sin nombre')
        description = node.get('description', '')
        
        text = f"**Nodo encontrado:**\n"
        text += f"- **Tipo:** {node_type}\n"
        text += f"- **Nombre:** {name}\n"
        if description:
            text += f"- **Descripción:** {description}\n"

        source = Source(
            id=str(node_id),
            title=f"Nodo: {name}",
            snippet=description or name,
            type=SourceType.GRAPH,
            url=f"graph://node/{node_id}",
            metadata=node
        )
        return text, source

    def _format_relationship(self, rel: Dict[str, Any], nodes_in_path: List[Dict[str, Any]]) -> Tuple[str, Source]:
        """Formatea una única relación y crea su objeto Source."""
        rel_id = rel.get('id', str(uuid.uuid4()))
        rel_type = rel.get('type', 'RELACIONADO_CON')
        start_node_id = rel.get('start_node')
        end_node_id = rel.get('end_node')

        # Buscar los nombres de los nodos en la lista de nodos del path
        start_node_name = self._find_node_name(start_node_id, nodes_in_path)
        end_node_name = self._find_node_name(end_node_id, nodes_in_path)

        text = f"**Relación encontrada:**\n"
        text += f"- De '{start_node_name}' a '{end_node_name}'\n"
        text += f"- **Tipo:** {rel_type}\n"

        source = Source(
            id=str(rel_id),
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
