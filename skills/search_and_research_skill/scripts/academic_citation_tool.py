"""
Herramienta de búsqueda, verificación y auditoría de fuentes académicas y científicas.
Consulta directamente registros oficiales (Crossref, OpenAlex, PubMed) para obtener
metadatos 100% verídicos (autores reales, títulos exactos, revistas oficiales, volumen, páginas y DOI),
eliminando cualquier posibilidad de alucinación bibliográfica.
"""

import logging
import re
import urllib.parse
import asyncio
from typing import Type, Optional, List, Dict, Any, Tuple
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool
from langchain_core.callbacks import AsyncCallbackManagerForToolRun

import httpx

from core.citation_models import Source, ToolOutputWithSources, SourceType
from core.agents.deep_researcher_utils import generate_stable_id

logger = logging.getLogger(__name__)

USER_AGENT = "KognitoAI-AcademicCitationVerifier/2.0 (mailto:admin@kognito.ai; Academic-Integrity-Guard)"


class AcademicCitationInput(BaseModel):
    """Esquema de entrada para la herramienta de verificación académica."""
    query: str = Field(
        description="Título del paper, apellidos de autores, DOI o texto de la cita a verificar/buscar.",
        json_schema_extra={"type": "string"}
    )
    mode: str = Field(
        default="verify",
        description="Modo de operación: 'verify' (para contrastar autores/título/revista con la fuente oficial), 'search' (para buscar literatura académica reciente sobre un tema), o 'doi' (para resolver un DOI directo).",
        json_schema_extra={"type": "string", "enum": ["verify", "search", "doi"]}
    )
    source: str = Field(
        default="all",
        description="Registro a consultar: 'crossref', 'openalex', 'pubmed' o 'all'.",
        json_schema_extra={"type": "string", "enum": ["all", "crossref", "openalex", "pubmed"]}
    )


class AcademicCitationTool(BaseTool):
    """
    Herramienta de verificación y búsqueda bibliográfica científica en registros oficiales indexados.
    Permite contrastar títulos, autores completos, revistas, volúmenes, páginas y DOIs reales,
    garantizando que ninguna cita o referencia bibliográfica sea inventada o distorsionada.
    """
    name: str = "academic_citation_verifier"
    description: str = (
        "Herramienta de verificación y búsqueda científica obligatoria para textos académicos y citas bibliográficas. "
        "Consulta en tiempo real Crossref, OpenAlex y PubMed para contrastar títulos de papers, autores reales completos, "
        "revistas oficiales, años, volúmenes, páginas y enlaces DOI. "
        "ÚSALA SIEMPRE antes de incluir referencias bibliográficas en un texto para garantizar que sean 100% verídicas y no alucinadas."
    )
    args_schema: Type[BaseModel] = AcademicCitationInput
    return_direct: bool = False
    account_id: Optional[str] = "api_user"
    workspace_id: Optional[str] = None
    telegram_id: Optional[int] = None
    thread_id: Optional[str] = None

    def _format_author_apa(self, family: str, given: str) -> str:
        """Formatea un autor en estilo APA (Apellido, I. N.)."""
        family = (family or "").strip()
        given = (given or "").strip()
        if not family:
            return given
        if not given:
            return family
        # Extraer iniciales
        given_parts = [p[0].upper() + "." for p in re.split(r"[\s\-]+", given) if p]
        initials = " ".join(given_parts)
        return f"{family}, {initials}"

    def _format_authors_list_apa(self, authors: List[Dict[str, str]]) -> str:
        """Formatea una lista completa de autores en APA 7 (hasta 20 autores sin omitir)."""
        if not authors:
            return "Autor desconocido"
        formatted = [self._format_author_apa(a.get("family", ""), a.get("given", "")) for a in authors]
        formatted = [f for f in formatted if f]
        if not formatted:
            return "Autor desconocido"
        if len(formatted) == 1:
            return formatted[0]
        if len(formatted) == 2:
            return f"{formatted[0]} & {formatted[1]}"
        if len(formatted) <= 20:
            return ", ".join(formatted[:-1]) + f", & {formatted[-1]}"
        # Más de 20 autores según APA 7
        return ", ".join(formatted[:19]) + ", ... " + formatted[-1]

    async def _query_crossref(self, client: httpx.AsyncClient, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Consulta el registro oficial de Crossref por metadatos o DOI."""
        items_out = []
        try:
            # Si la consulta parece un DOI directo
            doi_match = re.search(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", query)
            if doi_match:
                doi = doi_match.group(0).rstrip(".")
                url = f"https://api.crossref.org/works/{urllib.parse.quote(doi)}"
                resp = await client.get(url, timeout=9.0)
                if resp.status_code == 200:
                    item = resp.json().get("message", {})
                    items_out.append(self._parse_crossref_item(item))
                    return items_out

            url = "https://api.crossref.org/works"
            params = {
                "query.bibliographic": query,
                "rows": limit
            }
            resp = await client.get(url, params=params, timeout=10.0)
            if resp.status_code == 200:
                raw_items = resp.json().get("message", {}).get("items", [])
                for it in raw_items:
                    items_out.append(self._parse_crossref_item(it))
        except Exception as e:
            logger.warning(f"Error consultando Crossref para '{query}': {e}")
        return items_out

    def _parse_crossref_item(self, it: Dict[str, Any]) -> Dict[str, Any]:
        titles = it.get("title", [])
        title = titles[0] if titles else "Sin título"
        containers = it.get("container-title", [])
        journal = containers[0] if containers else ""
        year = None
        date_parts = it.get("issued", {}).get("date-parts", [[None]])
        if date_parts and date_parts[0] and date_parts[0][0]:
            year = date_parts[0][0]

        authors = []
        for a in it.get("author", []):
            authors.append({
                "family": a.get("family", ""),
                "given": a.get("given", "")
            })

        doi = it.get("DOI", "")
        return {
            "title": title,
            "journal": journal,
            "year": year,
            "volume": it.get("volume"),
            "issue": it.get("issue"),
            "page": it.get("page"),
            "doi": doi,
            "doi_url": f"https://doi.org/{doi}" if doi else "",
            "authors": authors,
            "source_db": "Crossref"
        }

    async def _query_openalex(self, client: httpx.AsyncClient, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Consulta el índice global de OpenAlex."""
        items_out = []
        try:
            url = "https://api.openalex.org/works"
            params = {"search": query, "per_page": limit}
            resp = await client.get(url, params=params, timeout=10.0)
            if resp.status_code == 200:
                results = resp.json().get("results", [])
                for r in results:
                    title = r.get("title") or "Sin título"
                    year = r.get("publication_year")
                    doi_url = r.get("doi") or ""
                    doi = doi_url.replace("https://doi.org/", "") if doi_url else ""
                    
                    loc = r.get("primary_location") or {}
                    source_obj = loc.get("source") or {}
                    journal = source_obj.get("display_name") or ""
                    
                    authors = []
                    for auth_ship in r.get("authorships", []):
                        auth = auth_ship.get("author", {})
                        disp_name = auth.get("display_name", "")
                        # Separar en nombre y apellido
                        parts = disp_name.split()
                        if len(parts) > 1:
                            family = parts[-1]
                            given = " ".join(parts[:-1])
                        else:
                            family = disp_name
                            given = ""
                        authors.append({"family": family, "given": given})

                    biblio = r.get("biblio") or {}
                    items_out.append({
                        "title": title,
                        "journal": journal,
                        "year": year,
                        "volume": biblio.get("volume"),
                        "issue": biblio.get("issue"),
                        "page": f"{biblio.get('first_page', '')}-{biblio.get('last_page', '')}".strip("-") or None,
                        "doi": doi,
                        "doi_url": doi_url or (f"https://doi.org/{doi}" if doi else ""),
                        "authors": authors,
                        "source_db": "OpenAlex"
                    })
        except Exception as e:
            logger.warning(f"Error consultando OpenAlex para '{query}': {e}")
        return items_out

    async def _query_pubmed(self, client: httpx.AsyncClient, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Consulta PubMed E-utilities para literatura biomédica y psicológica."""
        items_out = []
        try:
            # 1. Search ESearch
            search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            params = {
                "db": "pubmed",
                "term": query,
                "retmode": "json",
                "retmax": limit
            }
            resp = await client.get(search_url, params=params, timeout=9.0)
            if resp.status_code != 200:
                return []
            
            id_list = resp.json().get("esearchresult", {}).get("idlist", [])
            if not id_list:
                return []

            # 2. Fetch Summary
            sum_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
            sum_params = {
                "db": "pubmed",
                "id": ",".join(id_list),
                "retmode": "json"
            }
            sum_resp = await client.get(sum_url, params=sum_params, timeout=9.0)
            if sum_resp.status_code == 200:
                result_data = sum_resp.json().get("result", {})
                for pmid in id_list:
                    item_data = result_data.get(pmid)
                    if not item_data:
                        continue
                    title = item_data.get("title", "").rstrip(".")
                    journal = item_data.get("source", "")
                    pubdate = item_data.get("pubdate", "")
                    year_match = re.search(r"\b(19|20)\d{2}\b", pubdate)
                    year = int(year_match.group(0)) if year_match else None
                    
                    authors = []
                    for a in item_data.get("authors", []):
                        name = a.get("name", "")
                        parts = name.split()
                        if len(parts) > 1:
                            family = parts[0]
                            given = " ".join(parts[1:])
                        else:
                            family = name
                            given = ""
                        authors.append({"family": family, "given": given})

                    # Extraer DOI de articleids
                    doi = ""
                    for aid in item_data.get("articleids", []):
                        if aid.get("idtype") == "doi":
                            doi = aid.get("value", "")
                            break

                    items_out.append({
                        "title": title,
                        "journal": journal,
                        "year": year,
                        "volume": item_data.get("volume"),
                        "issue": item_data.get("issue"),
                        "page": item_data.get("pages"),
                        "doi": doi,
                        "doi_url": f"https://doi.org/{doi}" if doi else f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                        "authors": authors,
                        "source_db": "PubMed"
                    })
        except Exception as e:
            logger.warning(f"Error consultando PubMed para '{query}': {e}")
        return items_out

    def _build_apa_citation(self, item: Dict[str, Any]) -> str:
        """Construye la referencia bibliográfica formal y determinista en APA 7ma edición."""
        authors_str = self._format_authors_list_apa(item.get("authors", []))
        year_str = f"({item.get('year')})" if item.get("year") else "(s.f.)"
        title_str = (item.get("title") or "Sin título").rstrip(".") + "."
        
        journal_part = ""
        journal = item.get("journal")
        if journal:
            journal_part = f" *{journal}*"
            vol = item.get("volume")
            issue = item.get("issue")
            page = item.get("page")
            
            if vol and issue:
                journal_part += f", *{vol}*({issue})"
            elif vol:
                journal_part += f", *{vol}*"
            elif issue:
                journal_part += f", ({issue})"
                
            if page:
                journal_part += f", {page}."
            else:
                journal_part += "."

        doi_url = item.get("doi_url") or ""
        citation_parts = [authors_str, year_str, title_str]
        if journal_part:
            citation_parts.append(journal_part.strip())
        if doi_url:
            citation_parts.append(doi_url)

        return " ".join([p for p in citation_parts if p])

    async def _arun(
        self,
        query: str,
        mode: str = "verify",
        source: str = "all",
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Ejecuta la búsqueda y verificación científica asíncrona."""
        logger.info(f"🔬 [AcademicCitationTool] Ejecutando '{mode}' para: '{query}' en '{source}'")
        headers = {"User-Agent": USER_AGENT}

        async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
            records: List[Dict[str, Any]] = []

            if mode == "doi":
                records = await self._query_crossref(client, query, limit=1)
            else:
                # Si se solicita una fuente específica
                if source == "crossref":
                    records = await self._query_crossref(client, query, limit=4)
                elif source == "openalex":
                    records = await self._query_openalex(client, query, limit=4)
                elif source == "pubmed":
                    records = await self._query_pubmed(client, query, limit=4)
                else:
                    # 'all': Consultamos Crossref y OpenAlex concurrentemente
                    tasks = [
                        self._query_crossref(client, query, limit=3),
                        self._query_openalex(client, query, limit=3)
                    ]
                    # Si la query sugiere temas médicos/adicciones/salud
                    if any(term in query.lower() for term in ["health", "salud", "psych", "chemsex", "drug", "vih", "hiv", "med"]):
                        tasks.append(self._query_pubmed(client, query, limit=3))
                    
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    for r in results:
                        if isinstance(r, list):
                            records.extend(r)

            # Deduplicar por DOI o título normalizado
            unique_records = []
            seen_identifiers = set()
            for rec in records:
                doi = (rec.get("doi") or "").lower().strip()
                title_norm = re.sub(r"[^\w\s]", "", (rec.get("title") or "").lower())[:60]
                ident = doi if doi else title_norm
                if ident and ident not in seen_identifiers:
                    seen_identifiers.add(ident)
                    unique_records.append(rec)

            if not unique_records:
                msg = (
                    f"⚠️ NO SE ENCONTRÓ REGISTRO OFICIAL INDEXADO para '{query}'.\n"
                    "DIRECTIVA DE RIGUROSIDAD: Si vas a mencionar este estudio, NO inventes la revista ni los coautores. "
                    "Decláralo explícitamente como: '[Referencia no verificada en registros indexados: {query}]' "
                    "o cítalo como cita secundaria si fue extraído de otro documento."
                )
                return ToolOutputWithSources(context_for_llm=msg, sources=[]).model_dump()

            # Formatear contexto verificado para el LLM y generar Source objects
            output_lines = [
                f"### RESULTADOS DE VERIFICACIÓN CIENTÍFICA OFICIAL ({len(unique_records)} obras encontradas):",
                "Usa EXCLUSIVAMENTE los siguientes datos exactos. Queda prohibido alterar revistas o autores.\n"
            ]
            sources: List[Source] = []

            for idx, rec in enumerate(unique_records[:5], 1):
                apa_ref = self._build_apa_citation(rec)
                authors_names = [f"{a.get('family', '')}, {a.get('given', '')}" for a in rec.get("authors", [])]
                
                output_lines.append(f"**[{idx}] Cita APA 7 Oficial Verificada:**")
                output_lines.append(f"> {apa_ref}\n")
                output_lines.append(f"- **Título Exacto:** {rec.get('title')}")
                output_lines.append(f"- **Revista/Editorial:** {rec.get('journal') or 'No especificada en el registro'}")
                output_lines.append(f"- **Año:** {rec.get('year')}")
                output_lines.append(f"- **Autores Reales ({len(authors_names)}):** {', '.join(authors_names)}")
                if rec.get("volume") or rec.get("issue") or rec.get("page"):
                    output_lines.append(f"- **Vol/N°/Páginas:** Vol. {rec.get('volume')}, N° {rec.get('issue')}, pp. {rec.get('page')}")
                output_lines.append(f"- **Enlace Oficial (DOI):** {rec.get('doi_url')}")
                output_lines.append(f"- **Base de Datos:** {rec.get('source_db')}\n")

                # Crear objeto Source de KognitoAI
                source_id = generate_stable_id(rec.get("doi_url") or rec.get("title", ""), prefix="academic")
                source_obj = Source(
                    id=source_id,
                    title=f"{rec.get('title')} ({rec.get('year')})",
                    url=rec.get("doi_url") or f"academic://{rec.get('doi')}",
                    snippet=f"Referencia verificada en {rec.get('source_db')}: {apa_ref}",
                    type=SourceType.DOCUMENT,
                    metadata={
                        "academic_verified": True,
                        "doi": rec.get("doi"),
                        "journal": rec.get("journal"),
                        "authors": authors_names,
                        "year": rec.get("year"),
                        "source_db": rec.get("source_db")
                    }
                )
                sources.append(source_obj)

            context_text = "\n".join(output_lines)
            return ToolOutputWithSources(context_for_llm=context_text, sources=sources).model_dump()

    def _run(self, query: str, **kwargs) -> str:
        raise NotImplementedError("Utiliza la ejecución asíncrona (_arun).")


def create_academic_citation_tool(account_id: Optional[str] = "api_user") -> AcademicCitationTool:
    """Crea una instancia de la herramienta de verificación académica."""
    return AcademicCitationTool(account_id=account_id)
