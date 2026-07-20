import os
import sys
import logging
import asyncio
from typing import Type, Any, Optional, List
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

current_dir = os.path.dirname(os.path.abspath(__file__))
skill_dir = os.path.dirname(current_dir)
if skill_dir not in sys.path:
    sys.path.insert(0, skill_dir)

logger = logging.getLogger(__name__)


class SearchEthnographicLiteratureInput(BaseModel):
    query: str = Field(
        ...,
        description="Consulta o palabras clave para buscar literatura en antropología y ciencias sociales. Ejemplo: 'antropología digital identidad juventud'"
    )
    max_results: int = Field(
        default=15,
        description="Número máximo de artículos a devolver (default: 15)."
    )
    year_range_start: Optional[int] = Field(
        default=2018,
        description="Año mínimo de publicación."
    )
    year_range_end: Optional[int] = Field(
        default=2026,
        description="Año máximo de publicación."
    )


class SearchEthnographicLiteratureTool(BaseTool):
    name: str = "search_ethnographic_literature"
    description: str = (
        "Busca artículos académicos, preprints y publicaciones etnográficas/antropológicas en "
        "Semantic Scholar, CrossRef, SciELO, RedALyC, PubMed y arXiv sin requerir API keys."
    )
    args_schema: Type[BaseModel] = SearchEthnographicLiteratureInput
    account_id: Optional[str] = None
    workspace_id: Optional[str] = None

    async def _arun(
        self,
        query: str,
        max_results: int = 15,
        year_range_start: Optional[int] = 2018,
        year_range_end: Optional[int] = 2026,
        **kwargs: Any
    ) -> dict:
        try:
            from core.citation_models import Source, SourceType, ToolOutputWithSources, format_context_with_sources
        except ImportError:
            # Fallback: devolver texto simple si citation_models no está disponible
            logger.warning("core.citation_models no disponible. Retornando texto plano.")
            return await self._arun_plain_text(query, max_results, year_range_start, year_range_end)

        try:
            from agents.bibliomancer import BibliomancerAgent

            biblio = BibliomancerAgent()
            year_range = None
            if year_range_start and year_range_end:
                year_range = (year_range_start, year_range_end)

            sources_raw = await biblio.search(
                query=query,
                max_results=max_results,
                year_range=year_range
            )

            if not sources_raw:
                output = ToolOutputWithSources(
                    context_for_llm=f"No se encontraron publicaciones académicas para la búsqueda: '{query}'.",
                    sources=[]
                )
                return output.model_dump()

            # Construir objetos Source para el sistema de citas de KognitoAI
            kai_sources: List[Source] = []
            context_parts = []

            for i, doc in enumerate(sources_raw[:max_results], 1):
                title = doc.get("title", "Sin título")
                authors = doc.get("authors", [])
                authors_str = ", ".join(authors) if authors else "Autores no especificados"
                year = doc.get("year", "N/A")
                abstract = doc.get("abstract", "Sin resumen disponible.")
                url = doc.get("url", "")
                doi = doc.get("doi", "")
                source_api = doc.get("source_api", doc.get("source", "API"))
                venue = doc.get("venue", "")
                citations_count = doc.get("citations", 0)

                # Construir snippet legible para la UI
                snippet_parts = []
                if authors_str:
                    snippet_parts.append(f"Autores: {authors_str}")
                if year and year != "N/A":
                    snippet_parts.append(f"Año: {year}")
                if venue:
                    snippet_parts.append(f"Revista/Fuente: {venue}")
                if abstract:
                    snippet_parts.append(f"Resumen: {abstract[:300]}...")
                snippet = " | ".join(snippet_parts)

                # URL preferida: DOI > URL directa
                if doi and not url:
                    url = f"https://doi.org/{doi}"
                elif doi:
                    # Mantener la URL de la fuente, pero registrar el DOI en metadata
                    pass

                source = Source(
                    id=i,
                    title=f"{title} ({year})",
                    url=url or f"https://search.crossref.org/?q={query}",
                    snippet=snippet,
                    type=SourceType.DOCUMENT,
                    metadata={
                        "authors": authors,
                        "year": year,
                        "venue": venue,
                        "doi": doi,
                        "source_api": source_api,
                        "citations": citations_count,
                        "pdf_url": doc.get("pdf_url"),
                    }
                )
                kai_sources.append(source)

                # Construir contexto para el LLM con número de cita
                context_parts.append(
                    f"Fuente [{i}] - {title} ({year})\n"
                    f"Autores: {authors_str}\n"
                    f"Base de datos: {source_api}\n"
                    f"Resumen: {abstract[:400]}\n"
                    + (f"DOI: {doi}\n" if doi else "")
                    + (f"URL: {url}\n" if url else "")
                )

            context_for_llm = (
                f"### Literatura Académica Encontrada para '{query}' ({len(kai_sources)} resultados):\n\n"
                + "\n---\n".join(context_parts)
                + "\n\nUsa los números de fuente [1], [2], etc. al citar esta información en tu respuesta."
            )

            output = ToolOutputWithSources(
                context_for_llm=context_for_llm,
                sources=kai_sources
            )
            return output.model_dump()

        except Exception as e:
            logger.error(f"Error executing SearchEthnographicLiteratureTool: {e}", exc_info=True)
            try:
                from core.citation_models import ToolOutputWithSources
                output = ToolOutputWithSources(
                    context_for_llm=f"Error al buscar literatura etnográfica: {str(e)}",
                    sources=[]
                )
                return output.model_dump()
            except Exception:
                return {"context_for_llm": f"Error al buscar literatura etnográfica: {str(e)}", "sources": []}

    async def _arun_plain_text(self, query, max_results, year_range_start, year_range_end):
        """Fallback que retorna texto plano si citation_models no está disponible."""
        try:
            from agents.bibliomancer import BibliomancerAgent
            biblio = BibliomancerAgent()
            year_range = (year_range_start, year_range_end) if year_range_start and year_range_end else None
            sources = await biblio.search(query=query, max_results=max_results, year_range=year_range)
            if not sources:
                return f"No se encontraron publicaciones académicas para la búsqueda: '{query}'."
            output = f"### Fuentes Académicas Encontradas ({len(sources)}):\n\n"
            for i, src in enumerate(sources[:max_results], 1):
                output += f"**{i}. {src.get('title', 'Sin título')}** ({src.get('year', 'N/A')})\n"
                output += f"- **Autores**: {', '.join(src.get('authors', [])) or 'Desconocido'}\n"
                output += f"- **Resumen**: {src.get('abstract', '')[:250]}...\n\n"
            return output
        except Exception as e:
            return f"Error al buscar literatura etnográfica: {str(e)}"

    def _run(self, *args, **kwargs):
        return asyncio.run(self._arun(*args, **kwargs))
