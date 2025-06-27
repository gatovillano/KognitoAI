import asyncio
import re
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
