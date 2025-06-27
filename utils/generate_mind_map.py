import graphviz
import base64
import os
import asyncio
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

async def generate_visual_mindmap(mindmap_data: Dict[str, List[str]], topic: str) -> str:
    """
    Genera un mapa mental visual usando Graphviz a partir de la estructura de ideas.
    Devuelve la imagen en formato base64.

    Args:
        mindmap_data: Un diccionario donde las claves son ideas principales y los valores son listas de sub-ideas.
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
             fillcolor='#FF6347', # Tomato
             fontcolor='white',
             fontsize='20',
             style='filled,bold')

    # Añadir ideas principales y sub-ideas
    for main_idea, sub_ideas in mindmap_data.items():
        # Crear un ID válido para Graphviz (reemplazando caracteres especiales)
        main_idea_id = main_idea.replace(" ", "_").replace("-", "_").replace(":", "_").replace("/", "_").replace(".", "_").replace(",", "_").strip()
        if not main_idea_id: # Asegurar que el ID no esté vacío
            main_idea_id = f"main_idea_{hash(main_idea)}"

        dot.node(main_idea_id, main_idea,
                 fillcolor='#90EE90', # LightGreen
                 fontcolor='black',
                 fontsize='14',
                 style='filled')
        dot.edge('central_topic', main_idea_id, color='#FF6347', penwidth='2.0')

        for sub_idea in sub_ideas:
            sub_idea_id = sub_idea.replace(" ", "_").replace("-", "_").replace(":", "_").replace("/", "_").replace(".", "_").replace(",", "_").strip()
            if not sub_idea_id: # Asegurar que el ID no esté vacío
                sub_idea_id = f"sub_idea_{hash(sub_idea)}"

            dot.node(sub_idea_id, sub_idea,
                     fillcolor='#ADD8E6', # LightBlue
                     fontcolor='black',
                     shape='ellipse',
                     fontsize='10',
                     style='filled')
            dot.edge(main_idea_id, sub_idea_id, color='#6A5ACD') # SlateBlue

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
