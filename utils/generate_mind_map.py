# utils/generate_mind_map.py

import graphviz
import base64
import os
import asyncio
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

async def generate_visual_mindmap(main_topics: List[str], sub_topics: List[str], topic: str) -> str:
    """
    Genera un mapa mental visual usando Graphviz a partir de los temas y subtemas.
    Devuelve la imagen en formato base64.

    Args:
        main_topics: Una lista de temas principales.
        sub_topics: Una lista de subtemas.
        topic: El tema central del mapa mental.

    Returns:
        Una cadena Base64 de la imagen PNG generada, o una cadena vacía si hay un error.
    """
    logger.info(f"Iniciando la generación del mapa mental visual para el tema: {topic}")

    # Configuración general del grafo
    dot = graphviz.Digraph(
        comment=f'Mapa Mental de {topic}',
        graph_attr={
            'rankdir': 'TB',  # Top to Bottom
            'overlap': 'false',
            'splines': 'true',
            'fontsize': '16',
            'fontname': 'Helvetica'
        },
        node_attr={
            'shape': 'box',
            'style': 'filled',
            'fontname': 'Helvetica',
            'fontsize': '12',
            'margin': '0.2,0.1'
        },
        edge_attr={
            'color': 'gray',
            'fontname': 'Helvetica',
            'fontsize': '10'
        }
    )

    # Nodo central del tema
    dot.node('central_topic', topic,
             shape='doubleoctagon',
             fillcolor='#FF6347',  # Tomato
             fontcolor='white',
             fontsize='20',
             style='filled,bold')

    # Añadir temas principales
    for main_topic in main_topics:
        # Crear un ID válido para Graphviz (reemplazando caracteres especiales)
        main_topic_id = main_topic.replace(" ", "_").replace("-", "_").replace(":", "_").replace("/", "_").replace(".", "_").replace(",", "_").strip()
        if not main_topic_id:  # Asegurar que el ID no esté vacío
            main_topic_id = f"main_topic_{hash(main_topic)}"

        dot.node(main_topic_id, main_topic,
                 fillcolor='#90EE90',  # LightGreen
                 fontcolor='black',
                 fontsize='14',
                 style='filled')
        dot.edge('central_topic', main_topic_id, color='#FF6347', penwidth='2.0')

    # Añadir subtemas
    for sub_topic in sub_topics:
        # Crear un ID válido para Graphviz (reemplazando caracteres especiales)
        sub_topic_id = sub_topic.replace(" ", "_").replace("-", "_").replace(":", "_").replace("/", "_").replace(".", "_").replace(",", "_").strip()
        if not sub_topic_id:  # Asegurar que el ID no esté vacío
            sub_topic_id = f"sub_topic_{hash(sub_topic)}"

        dot.node(sub_topic_id, sub_topic,
                 fillcolor='#ADD8E6',  # LightBlue
                 fontcolor='black',
                 shape='ellipse',
                 fontsize='10',
                 style='filled')
        dot.edge(main_topic_id, sub_topic_id, color='#6A5ACD')  # SlateBlue

    # Renderizar a PNG y obtener los bytes
    try:
        # Generar un nombre de archivo temporal único para evitar colisiones
        temp_filename = f'mindmap_{os.urandom(16).hex()}'
        # El método render() de Graphviz devuelve la ruta al archivo generado
        # Ejecutar en un executor para no bloquear el bucle de eventos si es una operación pesada
        loop = asyncio.get_event_loop()
        output_path = await loop.run_in_executor(
            None,
            lambda: dot.render(filename=temp_filename, format='png', view=False, cleanup=True)
        )
        logger.info(f"Mapa mental renderizado a: {output_path}")

        # Leer el archivo generado
        with open(output_path, 'rb') as f:
            image_bytes = f.read()
        # Eliminar el archivo temporal inmediatamente
        os.remove(output_path)
        logger.info(f"Archivo temporal '{output_path}' eliminado.")

        # Codificar a base64 para poder pasarlo como string
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        logger.info("Mapa mental visual generado y codificado en Base64.")
        return base64_image

    except FileNotFoundError:
        logger.error("Graphviz no está instalado o no está en el PATH. Por favor, instálalo para generar mapas visuales.")
        return ""
    except Exception as e:
        logger.error(f"Error al generar el mapa mental visual con Graphviz: {e}", exc_info=True)
        return ""

# utils/mindmap_utils.py

from typing import List, Dict

def format_mindmap_data(concepts: str) -> Dict[str, List[str]]:
    """
    Formatea los datos extraídos por la herramienta de análisis de documentos
    para que sean compatibles con la función generate_visual_mindmap.
    """
    # Dividir los conceptos en temas principales y subtemas
    topics = [c.strip() for c in concepts.split(",")]
    main_topics = topics[:5]  # Tomar los primeros 5 como temas principales
    sub_topics = topics[5:]  # Tomar el resto como subtemas

    return {"main_topics": main_topics, "sub_topics": sub_topics}