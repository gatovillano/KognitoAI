"""
Utilidades para generar mapas mentales visuales usando Graphviz y MermaidJS.
Incluye funciones para crear mapas mentales tradicionales y dinámicos.
"""

import asyncio
import base64
import logging
import os
import re
from datetime import datetime
from typing import Dict, List, Any

import graphviz

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


async def generate_mermaid_mindmap(document_content: str, topic_hint: str = "", concept_query: str = "temas clave") -> str:
    """
    Genera un mapa mental usando sintaxis MermaidJS a partir del contenido del documento.

    Args:
        document_content: El contenido del documento a analizar
        topic_hint: Una pista sobre el tema principal del documento
        concept_query: La consulta para extraer conceptos clave

    Returns:
        Código MermaidJS para renderizar el mapa mental
    """
    try:
        from core.llm_manager import get_main_llm
        from utils.document_analysis import extract_concepts_from_document

        # 1. Extraer conceptos del documento
        concepts = await extract_concepts_from_document(document_content, concept_query, topic_hint)
        if not concepts:
            return "graph TD;\n    A[No se pudieron extraer conceptos] --> B[Error en el análisis]"

        # 2. Generar código MermaidJS con el LLM
        mermaid_prompt = f"""
        Basado en los siguientes conceptos extraídos de un documento, genera un mapa mental detallado y bien estructurado utilizando la sintaxis de MermaidJS.
        El tema principal es '{topic_hint or 'Concepto Central'}'.

        INSTRUCCIONES ESPECÍFICAS:
        1. Usa la sintaxis 'graph TD;' para empezar
        2. Organiza los conceptos de manera jerárquica y lógica
        3. Usa nodos con identificadores únicos (A, B, C, etc.)
        4. Conecta los nodos con flechas (-->)
        5. Agrupa conceptos relacionados bajo ramas principales
        6. Usa texto descriptivo en los nodos entre corchetes []
        7. Mantén una estructura clara y legible

        Responde ÚNICAMENTE con el código MermaidJS, sin explicaciones adicionales.

        Conceptos a estructurar:
        {concepts}
        """

        llm = get_main_llm()
        if not llm:
            raise RuntimeError("El LLM principal no está disponible.")

        response = await llm.ainvoke(mermaid_prompt)
        mermaid_code = response.content.strip()

        # Validación y limpieza del código Mermaid
        if "```mermaid" in mermaid_code:
            match = re.search(r"```mermaid\n(.*?)\n```", mermaid_code, re.DOTALL)
            if match:
                mermaid_code = match.group(1).strip()
        elif "```" in mermaid_code:
            # Remover cualquier bloque de código genérico
            mermaid_code = re.sub(r"```.*?\n(.*?)\n```", r"\1", mermaid_code, flags=re.DOTALL).strip()

        # Validar que el código comience con graph
        if not mermaid_code.lower().strip().startswith("graph"):
            # Si no es válido, crear un mapa mental básico
            logger.warning("El LLM no generó código Mermaid válido, creando estructura básica")
            return create_basic_mermaid_structure(concepts, topic_hint)

        return mermaid_code

    except Exception as e:
        logger.exception(f"Error al generar mapa mental Mermaid: {e}")
        return create_basic_mermaid_structure(concepts if 'concepts' in locals() else "Error en análisis", topic_hint)


def create_basic_mermaid_structure(concepts: str, topic_hint: str = "") -> str:
    """
    Crea una estructura básica de mapa mental Mermaid cuando el LLM falla.

    Args:
        concepts: Los conceptos extraídos del documento
        topic_hint: El tema principal

    Returns:
        Código MermaidJS básico
    """
    central_topic = topic_hint or "Tema Principal"
    topics = [c.strip() for c in concepts.split(",") if c.strip()]

    mermaid_lines = ["graph TD;"]
    mermaid_lines.append(f"    A[{central_topic}]")

    # Agregar conceptos principales
    for i, topic in enumerate(topics[:8], 1):  # Limitar a 8 conceptos para mantener legibilidad
        node_id = chr(65 + i)  # B, C, D, etc.
        clean_topic = topic.replace('"', "'").replace('[', '(').replace(']', ')')
        mermaid_lines.append(f"    {node_id}[{clean_topic}]")
        mermaid_lines.append(f"    A --> {node_id}")

    return "\n".join(mermaid_lines)


async def generate_mindmap_data_for_frontend(document_content: str, topic_hint: str = "", concept_query: str = "temas clave", account_id: str = "") -> Dict[str, Any]:
    """
    Genera datos estructurados para el frontend que incluyen tanto Mermaid como datos tradicionales.

    Args:
        document_content: El contenido del documento a analizar
        topic_hint: Una pista sobre el tema principal
        concept_query: La consulta para extraer conceptos
        account_id: ID de la cuenta del usuario

    Returns:
        Diccionario con datos estructurados para el frontend
    """
    try:
        # Generar código Mermaid
        mermaid_code = await generate_mermaid_mindmap(document_content, topic_hint, concept_query)

        # Extraer conceptos para datos adicionales
        from utils.document_analysis import extract_concepts_from_document
        concepts = await extract_concepts_from_document(document_content, concept_query, topic_hint)

        # Formatear datos tradicionales
        mindmap_data = format_mindmap_data(concepts) if concepts else {"main_topics": [], "sub_topics": []}

        return {
            "type": "mindmap_mermaid",
            "content": mermaid_code,
            "title": f"Mapa Mental: {topic_hint or 'Análisis de Documento'}",
            "metadata": {
                "analysis_type": "mindmap_mermaid",
                "topic": topic_hint or "Tema Principal",
                "concept_query": concept_query,
                "created_at": datetime.now().isoformat(),
                "tool_used": "mindmap_generator_tool.py"
            },
            "traditional_data": mindmap_data,
            "raw_concepts": concepts
        }

    except Exception as e:
        logger.exception(f"Error al generar datos del mapa mental: {e}")
        return {
            "type": "error",
            "content": f"Error al generar el mapa mental: {str(e)}",
            "title": "Error en Generación",
            "metadata": {
                "error": str(e),
                "created_at": datetime.now().isoformat()
            }
        }