# utils/collection_analysis.py

import asyncio
import re
from typing import List, Dict, Any
from core.llm_manager import get_fast_llm

# Función para dividir el texto en fragmentos con solapamiento
def _chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Divide un texto en fragmentos con un solapamiento especificado."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        if end >= len(text):
            break
        start += (chunk_size - overlap)
    return chunks

async def extract_concepts_from_document(document_content: str, concept_query: str, topic_hint: str) -> str:
    """
    Extrae conceptos clave o información específica de un documento utilizando un LLM,
    procesando el documento en fragmentos si es necesario.
    """
    llm = get_fast_llm()
    if llm is None:
        print("Error: No se pudo obtener la instancia del LLM rápido.")
        return ""

    # Definimos un tamaño de fragmento y solapamiento adecuados para Gemini.
    # Puedes ajustar estos valores. Gemini tiene una ventana de contexto muy grande,
    # pero es bueno mantener los fragmentos manejables para eficiencia y costo.
    CHUNK_SIZE = 10000  # Caracteres por fragmento
    OVERLAP = 1000      # Caracteres de solapamiento entre fragmentos

    all_extracted_concepts = []

    # Si el documento es más grande que el tamaño de un fragmento, lo dividimos
    if len(document_content) > CHUNK_SIZE:
        chunks = _chunk_text(document_content, CHUNK_SIZE, OVERLAP)
        print(f"Documento grande detectado. Dividiendo en {len(chunks)} fragmentos para procesamiento.")
        for i, chunk in enumerate(chunks):
            print(f"Procesando fragmento {i+1}/{len(chunks)}...")
            prompt = f"""Dado el siguiente fragmento de texto de un documento más grande, extrae los {concept_query} relacionados con el tema '{topic_hint if topic_hint else 'general'}'.
            Lista los {concept_query} como una lista de elementos separados por comas. No incluyas información redundante que ya esté en otros fragmentos.

            Fragmento de texto:
            ---
            {chunk}
            ---

            {concept_query.capitalize()} extraídos (separados por comas):
            """
            try:
                llm_response = await llm.ainvoke(prompt)
                extracted_from_chunk = llm_response.content.strip()
                if extracted_from_chunk:
                    all_extracted_concepts.append(extracted_from_chunk)
            except Exception as e:
                print(f"Error al extraer conceptos del fragmento {i+1} con LLM: {e}")
                # Continuar con los otros fragmentos incluso si uno falla
    else:
        # Si el documento es pequeño, lo procesamos de una vez
        prompt = f"""Dado el siguiente texto de un documento, extrae los {concept_query} relacionados con el tema '{topic_hint if topic_hint else 'general'}'.
        Lista los {concept_query} como una lista de elementos separados por comas.

        Texto del documento:
        ---
        {document_content}
        ---

        {concept_query.capitalize()} extraídos (separados por comas):
        """
        try:
            llm_response = await llm.ainvoke(prompt)
            extracted_from_chunk = llm_response.content.strip()
            if extracted_from_chunk:
                all_extracted_concepts.append(extracted_from_chunk)
        except Exception as e:
            print(f"Error al extraer conceptos del documento completo con LLM: {e}")

    # Paso final: Sintetizar y consolidar los conceptos extraídos de todos los fragmentos
    if not all_extracted_concepts:
        return ""

    # Unimos todos los conceptos extraídos para la síntesis final
    combined_concepts_text = ", ".join(all_extracted_concepts)

    # Llamada final al LLM para consolidar y eliminar duplicados
    synthesis_prompt = f"""Dados los siguientes {concept_query} extraídos de varias partes de un documento sobre el tema '{topic_hint if topic_hint else 'general'}',
    consolida, elimina duplicados y organiza la lista de manera coherente.
    Devuelve una lista final de {concept_query} importantes, separados por comas.

    {concept_query.capitalize()} iniciales:
    ---
    {combined_concepts_text}
    ---

    {concept_query.capitalize()} consolidados (separados por comas):
    """
    try:
        final_llm_response = await llm.ainvoke(synthesis_prompt)
        return final_llm_response.content.strip()
    except Exception as e:
        print(f"Error al sintetizar conceptos con LLM: {e}")
        # Si la síntesis falla, devolvemos los conceptos combinados sin sintetizar
        return combined_concepts_text

async def analyze_document_collection(documents: List[Dict[str, Any]], concept_query: str, collection_topic: str) -> Dict[str, Any]:
    """
    Analiza una colección de documentos para extraer conceptos clave y sintetizarlos en un análisis cohesivo.
    
    Args:
        documents: Lista de diccionarios, cada uno con 'title' y 'content' de un documento.
        concept_query: Tipo de conceptos a extraer (ej. 'temas clave', 'conceptos principales').
        collection_topic: Tema o categoría de la colección para guiar el análisis.
    
    Returns:
        Diccionario con los conceptos extraídos por documento y un resumen consolidado.
    """
    print(f"Analizando colección de {len(documents)} documentos sobre '{collection_topic}'...")
    
    # Extraer conceptos de cada documento individualmente
    extracted_concepts_per_doc = []
    for doc in documents:
        title = doc.get('title', 'Documento sin título')
        content = doc.get('content', '')
        print(f"Procesando documento: {title}")
        concepts = await extract_concepts_from_document(content, concept_query, collection_topic)
        if concepts:
            extracted_concepts_per_doc.append({
                'title': title,
                'concepts': concepts
            })
    
    # Sintetizar todos los conceptos extraídos en un análisis consolidado
    if not extracted_concepts_per_doc:
        return {
            'collection_topic': collection_topic,
            'document_concepts': [],
            'consolidated_concepts': 'No se extrajeron conceptos de la colección.'
        }
    
    # Preparar texto para síntesis final
    combined_text = "\n".join(
        [f"Documento '{entry['title']}': {entry['concepts']}" for entry in extracted_concepts_per_doc]
    )
    
    llm = get_fast_llm()
    if llm is None:
        print("Error: No se pudo obtener la instancia del LLM rápido para síntesis.")
        return {
            'collection_topic': collection_topic,
            'document_concepts': extracted_concepts_per_doc,
            'consolidated_concepts': 'Error al obtener LLM para síntesis.'
        }
    
    synthesis_prompt = f"""Analiza los siguientes {concept_query} extraídos de una colección de documentos sobre el tema '{collection_topic}'.
    Consolida la información, elimina duplicados y proporciona una lista final de los {concept_query} más importantes, separados por comas.
    Además, ofrece un breve resumen narrativo (máximo 100 palabras) sobre los temas principales de la colección.

    {concept_query.capitalize()} extraídos por documento:
    ---
    {combined_text}
    ---

    Respuesta en formato:
    Lista de {concept_query} consolidados (separados por comas):
    Resumen narrativo:
    """
    try:
        final_response = await llm.ainvoke(synthesis_prompt)
        response_text = final_response.content.strip()
        
        # Parsear la respuesta para separar lista y resumen
        consolidated_concepts = ""
        narrative_summary = ""
        lines = response_text.split("\n")
        for line in lines:
            if line.startswith("Lista de") or line.startswith("Lista consolidada"):
                consolidated_concepts = line.split(":", 1)[1].strip()
            elif line.startswith("Resumen narrativo:") or line.startswith("Resumen:"):
                narrative_summary = line.split(":", 1)[1].strip()
            elif consolidated_concepts and not narrative_summary:
                narrative_summary = line.strip()
        
        return {
            'collection_topic': collection_topic,
            'document_concepts': extracted_concepts_per_doc,
            'consolidated_concepts': consolidated_concepts,
            'narrative_summary': narrative_summary
        }
    except Exception as e:
        print(f"Error al sintetizar análisis de colección con LLM: {e}")
        return {
            'collection_topic': collection_topic,
            'document_concepts': extracted_concepts_per_doc,
            'consolidated_concepts': 'Error en síntesis final.',
            'narrative_summary': 'No disponible debido a error en síntesis.'
        }
