import os
import sys
import logging
import asyncio
from typing import Type, Any, Optional, List
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

# Garantizar resolución de módulos dentro de la skill
current_dir = os.path.dirname(os.path.abspath(__file__))
skill_dir = os.path.dirname(current_dir)
if skill_dir not in sys.path:
    sys.path.insert(0, skill_dir)

logger = logging.getLogger(__name__)


class RunEthnographicResearchInput(BaseModel):
    research_question: str = Field(
        ...,
        description="La pregunta o tema principal de investigación etnográfica. Ejemplo: '¿Cómo construyen los jóvenes su identidad digital en TikTok?'"
    )
    max_sources: int = Field(
        default=20,
        description="Número máximo de fuentes académicas a recuperar y analizar (default: 20)."
    )
    document_type: str = Field(
        default="ethnographic_report",
        description="Tipo de documento a generar: 'ethnographic_report' (informe etnográfico), 'systematic_review' (revisión sistemática) o 'field_notes_analysis' (análisis de campo)."
    )
    year_range_start: Optional[int] = Field(
        default=2018,
        description="Año de inicio para el filtro de literatura (ej. 2018)."
    )
    year_range_end: Optional[int] = Field(
        default=2026,
        description="Año de fin para el filtro de literatura (ej. 2026)."
    )
    citation_style: str = Field(
        default="apa",
        description="Estilo de citación académica: 'apa', 'mla', 'chicago' o 'aaa' (default: 'apa')."
    )


class RunEthnographicResearchTool(BaseTool):
    name: str = "run_ethnographic_research"
    description: str = (
        "Ejecuta un pipeline completo de investigación etnográfica o antropológica. "
        "Realiza búsqueda bibliográfica multi-API (Semantic Scholar, CrossRef, SciELO, RedALyC, PubMed), "
        "análisis temático, triangulación de fuentes y generación del documento académico final."
    )
    args_schema: Type[BaseModel] = RunEthnographicResearchInput
    account_id: Optional[str] = None
    workspace_id: Optional[str] = None

    async def _arun(
        self,
        research_question: str,
        max_sources: int = 20,
        document_type: str = "ethnographic_report",
        year_range_start: Optional[int] = 2018,
        year_range_end: Optional[int] = 2026,
        citation_style: str = "apa",
        **kwargs: Any
    ) -> dict:
        try:
            from core.citation_models import Source, SourceType, ToolOutputWithSources
        except ImportError:
            logger.warning("core.citation_models no disponible. Retornando texto plano.")
            return await self._arun_plain_text(
                research_question, max_sources, document_type,
                year_range_start, year_range_end, citation_style
            )

        try:
            from scripts.orchestrator import KAIEthnoOrchestrator

            orchestrator = KAIEthnoOrchestrator(
                enable_ethics=True,
                enable_memory=False,
                enable_message_bus=False
            )

            year_range = None
            if year_range_start and year_range_end:
                year_range = (year_range_start, year_range_end)

            result = await orchestrator.run_research(
                research_question=research_question,
                max_sources=max_sources,
                year_range=year_range,
                include_visualizations=True,
                generate_document=True,
                document_type=document_type,
                citation_style=citation_style
            )

            kai_sources: List[Source] = []
            context_parts = []

            if isinstance(result, dict):
                status = result.get("status", "completed")
                document_content = result.get("document", {}).get("content", "") if isinstance(result.get("document"), dict) else ""
                summary = result.get("summary", "")
                metrics = result.get("metrics", {})
                bibliography = result.get("bibliography", [])
                collected_sources = result.get("sources", [])

                # --- Fuente 1: El documento académico generado ---
                doc_snippet = document_content[:600] + "..." if len(document_content) > 600 else document_content
                if not doc_snippet:
                    doc_snippet = summary[:600] if summary else f"Investigación completada. Estado: {status}."

                kai_sources.append(Source(
                    id=1,
                    title=f"Informe de Investigación: {research_question[:80]}",
                    url="memory://ethnographic_research_report",
                    snippet=doc_snippet,
                    type=SourceType.DOCUMENT,
                    metadata={
                        "document_type": document_type,
                        "citation_style": citation_style,
                        "status": status,
                        "metrics": metrics,
                    }
                ))

                context_parts.append(
                    f"Documento Generado [1] – {document_type} ({citation_style.upper()}):\n"
                    f"Estado: {status}\n"
                    + (f"Resumen ejecutivo: {summary}\n" if summary else "")
                    + (f"Contenido: {doc_snippet}\n" if doc_snippet else "")
                )

                # --- Fuentes 2+: Literatura bibliográfica recolectada ---
                source_list = bibliography if bibliography else collected_sources
                for i, src in enumerate(source_list[:max_sources], 2):
                    if isinstance(src, dict):
                        title = src.get("title", "Fuente bibliográfica")
                        authors = src.get("authors", [])
                        authors_str = ", ".join(authors) if isinstance(authors, list) else str(authors)
                        year = src.get("year", "N/A")
                        url = src.get("url", "")
                        doi = src.get("doi", "")
                        abstract = src.get("abstract", "")
                        source_api = src.get("source_api", src.get("source", "API"))

                        if doi and not url:
                            url = f"https://doi.org/{doi}"

                        snippet = (
                            f"Autores: {authors_str} | Año: {year}"
                            + (f" | {source_api}" if source_api else "")
                            + (f" | {abstract[:200]}..." if abstract else "")
                        )

                        kai_sources.append(Source(
                            id=i,
                            title=f"{title} ({year})",
                            url=url or f"https://search.crossref.org/?q={title}",
                            snippet=snippet,
                            type=SourceType.DOCUMENT,
                            metadata={
                                "authors": authors,
                                "year": year,
                                "doi": doi,
                                "source_api": source_api,
                                "citations": src.get("citations", 0),
                            }
                        ))

                        context_parts.append(
                            f"Fuente Bibliográfica [{i}] – {title} ({year})\n"
                            f"Autores: {authors_str}\n"
                            + (f"DOI: {doi}\n" if doi else "")
                            + (f"Resumen: {abstract[:300]}\n" if abstract else "")
                        )

                # Métricas al final del contexto
                if metrics:
                    metrics_str = ", ".join(f"{k}: {v}" for k, v in metrics.items())
                    context_parts.append(f"Métricas del pipeline: {metrics_str}")

            else:
                # Resultado inesperado
                context_parts.append(f"Resultado de investigación: {str(result)[:800]}")
                kai_sources.append(Source(
                    id=1,
                    title=f"Investigación Etnográfica: {research_question[:80]}",
                    url="memory://ethnographic_research",
                    snippet=str(result)[:400],
                    type=SourceType.DOCUMENT,
                    metadata={}
                ))

            context_for_llm = (
                f"### Investigación Etnográfica Completa: {research_question}\n\n"
                + "\n\n---\n\n".join(context_parts)
                + "\n\nUsa los números de fuente [1], [2], etc. al referenciar cada sección "
                "o fuente bibliográfica en tu respuesta."
            )

            output = ToolOutputWithSources(
                context_for_llm=context_for_llm,
                sources=kai_sources
            )
            return output.model_dump()

        except Exception as e:
            logger.error(f"Error executing RunEthnographicResearchTool: {e}", exc_info=True)
            try:
                from core.citation_models import ToolOutputWithSources
                output = ToolOutputWithSources(
                    context_for_llm=f"Error al ejecutar la investigación etnográfica: {str(e)}",
                    sources=[]
                )
                return output.model_dump()
            except Exception:
                return {"context_for_llm": f"Error al ejecutar la investigación etnográfica: {str(e)}", "sources": []}

    async def _arun_plain_text(
        self, research_question, max_sources, document_type,
        year_range_start, year_range_end, citation_style
    ):
        """Fallback que retorna texto plano si citation_models no está disponible."""
        try:
            from scripts.orchestrator import KAIEthnoOrchestrator
            orchestrator = KAIEthnoOrchestrator(enable_ethics=True, enable_memory=False, enable_message_bus=False)
            year_range = (year_range_start, year_range_end) if year_range_start and year_range_end else None
            result = await orchestrator.run_research(
                research_question=research_question,
                max_sources=max_sources,
                year_range=year_range,
                include_visualizations=True,
                generate_document=True,
                document_type=document_type,
                citation_style=citation_style
            )
            if isinstance(result, dict):
                status = result.get("status", "completed")
                document = result.get("document", {}).get("content", "") if isinstance(result.get("document"), dict) else ""
                summary = result.get("summary", "")
                output = f"### Resultado de Investigación Etnográfica: {research_question}\n**Estado**: {status}\n\n"
                if summary:
                    output += f"**Resumen**: {summary}\n\n"
                if document:
                    output += f"### Documento Generado:\n\n{document}\n"
                else:
                    output += f"Resultados procesados: {result.get('metrics', {})}"
                return output
            return str(result)
        except Exception as e:
            return f"Error al ejecutar la investigación etnográfica: {str(e)}"

    def _run(self, *args, **kwargs):
        return asyncio.run(self._arun(*args, **kwargs))
