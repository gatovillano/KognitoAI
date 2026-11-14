"""
Módulo de auditoría y verificación bibliográfica científica para KognitoAI.
Permite analizar textos, tesinas o borradores, extraer las referencias y contrastarlas
con registros oficiales (Crossref, OpenAlex, PubMed), detectando alucinaciones de revistas,
títulos o autores y generando la versión 100% verídica en APA 7.
"""

import re
import asyncio
import logging
from typing import List, Dict, Any, Optional

from skills.search_and_research_skill.scripts.academic_citation_tool import AcademicCitationTool

logger = logging.getLogger(__name__)


def extract_bibliography_entries(text: str) -> List[str]:
    """
    Extrae las entradas de la sección de Bibliografía o Referencias de un informe.
    """
    if not text:
        return []

    # Localizar sección de bibliografía o referencias
    biblio_match = re.search(
        r"(?:##+\s*(?:7\.\s*)?(?:Bibliograf[íi]a|Referencias|Fuentes\s+Consultadas|References)[^\n]*\n)([\s\S]*?)(?:<visual_schema>|##|\Z)",
        text,
        re.IGNORECASE
    )
    
    entries = []
    if biblio_match:
        section_content = biblio_match.group(1).strip()
        # Dividir por líneas o elementos numerados / viñetas
        raw_lines = re.split(r"\n(?=\s*(?:[-*•]|\d+[\.\)]|\[\d+\]))", section_content)
        for line in raw_lines:
            cleaned = re.sub(r"^[\s\-*•\d\.\)\[\]]+", "", line).strip()
            # Ignorar cabeceras vacías o notas cortas
            if len(cleaned) > 20 and not cleaned.startswith("#"):
                entries.append(cleaned)
    
    # Si no se encontró sección formal, buscar citas típicas en formato Autor (Año)
    if not entries:
        pattern = r"([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+(?:et\s+al\.|y|&|,)\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*\s*\((?:19|20)\d{2}\)[^.\n]+(?:\.|\n))"
        matches = re.findall(pattern, text)
        for m in matches:
            m_clean = m.strip()
            if len(m_clean) > 25 and m_clean not in entries:
                entries.append(m_clean)

    return entries


async def verify_single_reference(raw_ref: str, tool: Optional[AcademicCitationTool] = None) -> Dict[str, Any]:
    """
    Verifica una referencia bibliográfica individual contra Crossref y OpenAlex.
    Detecta si la revista o los autores fueron alterados/inventados.
    """
    if tool is None:
        tool = AcademicCitationTool()

    # Limpiar query: extraer título y autor clave
    # Si tiene DOI directo, usarlo
    doi_match = re.search(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", raw_ref)
    if doi_match:
        query = doi_match.group(0).rstrip(".")
        mode = "doi"
    else:
        # Remover URLs genéricas y caracteres sobrantes
        clean_query = re.sub(r"https?://\S+", "", raw_ref)
        clean_query = re.sub(r"\[.*?\]|\(.*?\)", " ", clean_query)
        clean_query = " ".join(clean_query.split()[:15])  # Primeras 15 palabras clave
        query = clean_query
        mode = "verify"

    try:
        result = await tool._arun(query=query, mode=mode, source="all")
        sources = result.get("sources", [])
        
        if not sources:
            return {
                "original": raw_ref,
                "verified": False,
                "confidence": 0.0,
                "message": "No se encontró registro indexado oficial en Crossref ni OpenAlex.",
                "verified_apa": None,
                "doi": None,
                "discrepancies": ["No indexado en registros abiertos"]
            }

        best_source = sources[0]
        meta = best_source.get("metadata") if isinstance(best_source, dict) else getattr(best_source, "metadata", {})
        meta = meta or {}
        snippet = best_source.get("snippet", "") if isinstance(best_source, dict) else getattr(best_source, "snippet", "")
        title = best_source.get("title", "") if isinstance(best_source, dict) else getattr(best_source, "title", "")
        source_url = best_source.get("url", "") if isinstance(best_source, dict) else getattr(best_source, "url", "")
        
        verified_apa = snippet.replace("Referencia verificada en Crossref: ", "").replace("Referencia verificada en OpenAlex: ", "")
        
        # Detectar discrepancias entre la cita original y la oficial
        discrepancies = []
        verified_journal = (meta.get("journal") or "").lower()
        if verified_journal and len(verified_journal) > 4:
            if verified_journal not in raw_ref.lower():
                discrepancies.append(f"Revista distorsionada: registro oficial indica '{meta.get('journal')}'")

        verified_authors = meta.get("authors", [])
        if verified_authors:
            # Comprobar si los autores principales aparecen
            first_author_family = (verified_authors[0].split(",")[0] if "," in verified_authors[0] else verified_authors[0]).strip().lower()
            if first_author_family and first_author_family not in raw_ref.lower():
                discrepancies.append(f"Primer autor oficial es '{verified_authors[0]}'")

        return {
            "original": raw_ref,
            "verified": True,
            "confidence": 0.95 if not discrepancies else 0.85,
            "verified_apa": verified_apa,
            "title": title,
            "journal": meta.get("journal"),
            "year": meta.get("year"),
            "authors": verified_authors,
            "doi": meta.get("doi"),
            "doi_url": source_url,
            "source_db": meta.get("source_db"),
            "discrepancies": discrepancies
        }
    except Exception as e:
        logger.error(f"Error al verificar referencia '{raw_ref}': {e}")
        return {
            "original": raw_ref,
            "verified": False,
            "error": str(e),
            "discrepancies": [f"Error de consulta: {e}"]
        }


async def audit_report_bibliography(report_text: str) -> Dict[str, Any]:
    """
    Audita exhaustivamente todas las referencias bibliográficas de un documento o informe.
    Retorna el estado de verificación, las correcciones necesarias y la lista verificada.
    """
    entries = extract_bibliography_entries(report_text)
    if not entries:
        return {
            "total_references": 0,
            "verified_count": 0,
            "hallucinated_or_unverified": 0,
            "results": [],
            "corrected_bibliography": ""
        }

    tool = AcademicCitationTool()
    tasks = [verify_single_reference(entry, tool) for entry in entries]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    verified_count = 0
    hallucinated_or_unverified = 0
    formatted_results = []
    corrected_entries = []

    for idx, r in enumerate(results, 1):
        if isinstance(r, dict):
            formatted_results.append(r)
            if r.get("verified") and not r.get("discrepancies"):
                verified_count += 1
                corrected_entries.append(f"- {r.get('verified_apa')}")
            elif r.get("verified") and r.get("discrepancies"):
                hallucinated_or_unverified += 1
                # Usar la versión corregida de la API
                corrected_entries.append(f"- {r.get('verified_apa')} *(Corregido: {'; '.join(r.get('discrepancies'))})*")
            else:
                hallucinated_or_unverified += 1
                corrected_entries.append(f"- ⚠️ {r.get('original')} *[No verificada en registros oficiales]*")
        else:
            hallucinated_or_unverified += 1
            corrected_entries.append(f"- ⚠️ {entries[idx-1]} *[Error en validación]*")

    corrected_biblio = "### Bibliografía Oficial Verificada (APA 7):\n" + "\n".join(corrected_entries)

    return {
        "total_references": len(entries),
        "verified_count": verified_count,
        "hallucinated_or_unverified": hallucinated_or_unverified,
        "results": formatted_results,
        "corrected_bibliography": corrected_biblio
    }
