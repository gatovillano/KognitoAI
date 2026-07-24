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


class AnalyzeEthnographicDataInput(BaseModel):
    text_content: str = Field(
        ...,
        description="El texto de transcripción, grupo focal o notas de trabajo de campo a analizar."
    )
    anonymize_pii: bool = Field(
        default=True,
        description="Si es True, anonimiza automáticamente datos personales identificables (email, teléfonos, nombres)."
    )
    coding_framework: str = Field(
        default="braun_clarke",
        description="Marco metodológico de codificación temática ('braun_clarke' o 'grounded_theory')."
    )


class AnalyzeEthnographicDataTool(BaseTool):
    name: str = "analyze_ethnographic_data"
    description: str = (
        "Analiza cualitativamente textos etnográficos, transcripciones de entrevistas o notas de campo. "
        "Realiza detección y anonimización de PII, codificación temática (Braun & Clarke / Grounded Theory) "
        "y extracción de redes semánticas."
    )
    args_schema: Type[BaseModel] = AnalyzeEthnographicDataInput
    account_id: Optional[str] = None
    workspace_id: Optional[str] = None

    async def _arun(
        self,
        text_content: str,
        anonymize_pii: bool = True,
        coding_framework: str = "braun_clarke",
        **kwargs: Any
    ) -> dict:
        try:
            from core.citation_models import Source, SourceType, ToolOutputWithSources
        except ImportError:
            logger.warning("core.citation_models no disponible. Retornando texto plano.")
            return await self._arun_plain_text(text_content, anonymize_pii, coding_framework)

        try:
            from agents.ethnograph import EthnographAgent
            from agents.pattern_finder import PatternFinderAgent

            ethnograph = EthnographAgent()
            pattern_finder = PatternFinderAgent()

            source_item = {
                "id": "user_input_transcript",
                "title": "Transcripción/Notas de Campo",
                "abstract": text_content,
                "content": text_content
            }

            processed = await ethnograph.process_corpus([source_item])
            patterns = await pattern_finder.analyze(processed)

            # --- Construir contexto para el LLM ---
            context_parts = []
            kai_sources: List[Source] = []

            # Fuente 1: El texto de análisis procesado
            pii_count = 0
            themes = []
            if processed:
                item = processed[0]
                pii_count = len(item.get("pii_detected", []))
                themes = item.get("themes", [])

            theme_names = [t.get("name", str(t)) for t in themes] if themes else []
            text_snippet = text_content[:500] + ("..." if len(text_content) > 500 else "")

            context_parts.append(
                f"Análisis Etnográfico del Corpus [1]:\n"
                f"- PII detectados y anonimizados: {pii_count}\n"
                f"- Marco metodológico: {coding_framework}\n"
                f"- Temas codificados: {', '.join(theme_names) if theme_names else 'En proceso de codificación'}\n"
                f"- Extracto del corpus: {text_snippet}"
            )

            kai_sources.append(Source(
                id=1,
                title="Corpus Analizado – Transcripción/Notas de Campo",
                url="memory://ethnographic_corpus_analysis",
                snippet=text_snippet,
                type=SourceType.DOCUMENT,
                metadata={
                    "pii_detected": pii_count,
                    "coding_framework": coding_framework,
                    "themes": theme_names,
                    "anonymized": anonymize_pii,
                }
            ))

            # Fuente 2+: Patrones y redes semánticas extraídos
            if patterns:
                keywords = patterns.get("keywords", {})
                clusters = patterns.get("clusters", [])
                networks = patterns.get("networks", [])

                top_keywords = (
                    list(keywords.keys())[:15] if isinstance(keywords, dict)
                    else keywords[:15] if isinstance(keywords, list)
                    else []
                )
                cluster_count = len(clusters) if clusters else 0
                network_count = len(networks) if networks else 0

                patterns_snippet = (
                    f"Palabras clave principales: {', '.join(top_keywords)}. "
                    f"Clusters temáticos: {cluster_count}. "
                    f"Redes semánticas identificadas: {network_count}."
                )

                context_parts.append(
                    f"Patrones y Redes Semánticas [2]:\n"
                    f"- Palabras clave: {', '.join(top_keywords)}\n"
                    f"- Clusters temáticos identificados: {cluster_count}\n"
                    f"- Redes semánticas: {network_count}\n"
                )

                kai_sources.append(Source(
                    id=2,
                    title="Análisis de Patrones Semánticos",
                    url="memory://pattern_analysis",
                    snippet=patterns_snippet,
                    type=SourceType.MEMORY,
                    metadata={
                        "keywords": top_keywords,
                        "cluster_count": cluster_count,
                        "network_count": network_count,
                    }
                ))

            context_for_llm = (
                "### Resultados del Análisis Etnográfico Cualitativo\n\n"
                + "\n\n".join(context_parts)
                + "\n\nUsa los números de fuente [1], [2], etc. al referenciar los hallazgos en tu respuesta."
            )

            output = ToolOutputWithSources(
                context_for_llm=context_for_llm,
                sources=kai_sources
            )
            return output.model_dump()

        except Exception as e:
            logger.error(f"Error executing AnalyzeEthnographicDataTool: {e}", exc_info=True)
            try:
                from core.citation_models import ToolOutputWithSources
                output = ToolOutputWithSources(
                    context_for_llm=f"Error al analizar datos etnográficos: {str(e)}",
                    sources=[]
                )
                return output.model_dump()
            except Exception:
                return {"context_for_llm": f"Error al analizar datos etnográficos: {str(e)}", "sources": []}

    async def _arun_plain_text(self, text_content, anonymize_pii, coding_framework):
        """Fallback que retorna texto plano si citation_models no está disponible."""
        try:
            from agents.ethnograph import EthnographAgent
            from agents.pattern_finder import PatternFinderAgent
            ethnograph = EthnographAgent()
            pattern_finder = PatternFinderAgent()
            source_item = {"id": "user_input_transcript", "title": "Transcripción", "abstract": text_content, "content": text_content}
            processed = await ethnograph.process_corpus([source_item])
            patterns = await pattern_finder.analyze(processed)
            output = "### Análisis Etnográfico Cualitativo\n\n"
            if processed:
                item = processed[0]
                output += f"- **PII Detectados**: {len(item.get('pii_detected', []))}\n"
                output += f"- **Temas**: {', '.join([t.get('name', str(t)) for t in item.get('themes', [])])}\n\n"
            if patterns:
                kw = patterns.get("keywords", {})
                top_kw = list(kw.keys())[:10] if isinstance(kw, dict) else kw[:10]
                output += f"- **Palabras clave**: {', '.join(top_kw)}\n"
            return output
        except Exception as e:
            return f"Error al analizar datos etnográficos: {str(e)}"

    def _run(self, *args, **kwargs):
        return asyncio.run(self._arun(*args, **kwargs))
