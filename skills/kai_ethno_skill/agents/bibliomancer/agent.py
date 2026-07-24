"""
Bibliomancer Agent - Cazador de Textos
Agente especializado en recolección bibliográfica sistemática
"""

import asyncio
import aiohttp
import logging
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional
from datetime import datetime
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class BibliomancerSearchResult(list):
    """
    Subclase de list que también soporta .get() para ser compatible tanto con
    código que espera List[Dict] (como search_ethnographic_literature.py)
    como código que espera un Dict con 'sources' o 'documents' (como orchestrator.py).
    """
    def __init__(self, items: list = None, raw_dict: dict = None):
        super().__init__(items or [])
        self.raw_dict = raw_dict or {}

    def get(self, key: str, default: Any = None) -> Any:
        if key in ("sources", "documents", "collected_docs", "validated_docs"):
            return list(self)
        return self.raw_dict.get(key, default)


class BibliomancerState(BaseModel):
    """Estado del agente Bibliomancer"""
    query: str = ""
    databases: List[str] = Field(default_factory=lambda: ["semantic_scholar", "arxiv", "crossref"])
    filters: Dict[str, Any] = Field(default_factory=dict)
    collected_docs: List[Dict[str, Any]] = Field(default_factory=list)
    validated_docs: List[Dict[str, Any]] = Field(default_factory=list)
    status: str = "idle"
    error: Optional[str] = None


class BibliomancerAgent:
    """
    Agente Bibliomancer - Especialista en recolección bibliográfica
    
    Capacidades:
    - Búsqueda en Semantic Scholar, arXiv, CrossRef (APIs públicas)
    - Filtrado por año, tipo de documento, idioma
    - Validación de fuentes (peer-review, impacto, fecha)
    - Exportación en formatos académicos (BibTeX, RIS, CSV)
    """
    
    name = "bibliomancer"
    description = "Cazador de Textos - Recolección bibliográfica sistemática"
    
    def __init__(self, llm_service: Any = None):
        self.llm = llm_service
        self.graph = self._build_graph()
        self.state = BibliomancerState()
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
    
    def _interpret_query(self, state: BibliomancerState) -> Dict[str, Any]:
        """Interpreta la consulta de búsqueda y extrae términos clave"""
        query = state.query.strip()
        if not query:
            return {"status": "error", "error": "Query vacía"}
        # Tokenización simple: dividir por espacios y filtrar stopwords básicas
        stopwords = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "el", "la", "los", "las", "un", "una", "de", "del", "y", "o", "en", "para", "por", "con"}
        terms = [t.lower().strip('.,;:!?()[]{}') for t in query.split() if t.lower() not in stopwords and len(t) > 2]
        state.filters.setdefault("terms", terms)
        return {"status": "query_interpreted", "terms": terms}

    def _search_databases_node(self, state: BibliomancerState) -> Dict[str, Any]:
        """Busca en las bases de datos configuradas"""
        return {"status": "searched", "collected_docs": state.collected_docs}

    def _validate_sources(self, state: BibliomancerState) -> Dict[str, Any]:
        """Valida la calidad de las fuentes encontradas"""
        validated = []
        for doc in state.collected_docs:
            score = 0.0
            checks = []
            
            # 1. Tiene título y abstract
            if doc.get("title") and doc.get("abstract"):
                score += 0.3
                checks.append("complete_metadata")
            
            # 2. Tiene DOI o URL estable
            if doc.get("doi") or doc.get("url"):
                score += 0.2
                checks.append("persistent_identifier")
            
            # 3. Año dentro de rango (si hay filtro)
            year = doc.get("year")
            if year and state.filters.get("year_from") and state.filters.get("year_to"):
                if state.filters["year_from"] <= int(year) <= state.filters["year_to"]:
                    score += 0.2
                    checks.append("date_range")
            elif year and int(year) >= 2015:
                score += 0.2
                checks.append("recent")
            
            # 4. Tipo de documento válido
            doc_type = doc.get("type", "").lower()
            valid_types = {"article", "journal article", "conference paper", "preprint", "book", "book chapter"}
            if doc_type in valid_types or not doc_type:
                score += 0.15
                checks.append("valid_type")
            
            # 5. Tiene autores
            if doc.get("authors"):
                score += 0.15
                checks.append("authored")
            
            doc["quality_score"] = score
            doc["validation_checks"] = checks
            
            if score >= 0.5:
                validated.append(doc)
        
        # Ordenar por score descendente
        validated.sort(key=lambda x: x.get("quality_score", 0), reverse=True)
        return {"status": "validated", "validated_docs": validated}

    def _export_results(self, state: BibliomancerState) -> Dict[str, Any]:
        """Exporta resultados en formato académico"""
        docs = state.validated_docs
        bibtex = self._export_bibtex(docs)
        csv_rows = self._export_csv(docs)
        return {
            "status": "completed",
            "bibtex": bibtex,
            "csv": csv_rows,
            "count": len(docs)
        }

    def _build_graph(self) -> StateGraph:
        """Construye el grafo de LangGraph para el flujo del agente"""
        workflow = StateGraph(BibliomancerState)
        
        workflow.add_node("interpret", self._interpret_query)
        workflow.add_node("search", self._search_databases_node)
        workflow.add_node("validate", self._validate_sources)
        workflow.add_node("export", self._export_results)
        
        workflow.set_entry_point("interpret")
        workflow.add_edge("interpret", "search")
        workflow.add_edge("search", "validate")
        workflow.add_edge("validate", "export")
        workflow.add_edge("export", END)
        
        return workflow.compile()
        
        workflow.set_entry_point("interpret")
        workflow.add_edge("interpret", "search")
        workflow.add_edge("search", "validate")
        workflow.add_edge("validate", "export")
        workflow.add_edge("export", END)
        
        return workflow.compile()
    
    async def run(self, query: str, databases: List[str] = None,
                  filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Ejecuta el agente con una consulta de búsqueda
        
        Args:
            query: Término de búsqueda o pregunta de investigación
            databases: Lista de bases de datos a consultar
            filters: Filtros adicionales (año, idioma, tipo de documento)
        
        Returns:
            Dict con documentos encontrados y metadata
        """
        self.state.query = query
        self.state.databases = databases or self.state.databases
        self.state.filters = filters or {}
        self.state.status = "running"
        self.state.collected_docs = []
        self.state.validated_docs = []
        
        try:
            # Fase 1: Interpretar query (sync node)
            interp_result = self._interpret_query(self.state)
            if interp_result.get("status") == "error":
                return {"status": "error", "error": interp_result["error"], "documents": []}
            
            # Fase 2: Buscar en cada base de datos (async)
            session = await self._get_session()
            search_tasks = []
            for db in self.state.databases:
                if db == "semantic_scholar":
                    search_tasks.append(self._search_semantic_scholar(session, query, filters))
                elif db == "arxiv":
                    search_tasks.append(self._search_arxiv(session, query, filters))
                elif db == "crossref":
                    search_tasks.append(self._search_crossref(session, query, filters))
                elif db == "scielo":
                    search_tasks.append(self._search_scielo(session, query, filters))
                elif db == "redalyc":
                    search_tasks.append(self._search_redalyc(session, query, filters))
                elif db == "pubmed":
                    search_tasks.append(self._search_pubmed(session, query, filters))
                else:
                    logger.warning(f"Base de datos no soportada: {db}")
            
            results = await asyncio.gather(*search_tasks, return_exceptions=True)
            
            for res in results:
                if isinstance(res, Exception):
                    logger.error(f"Error en búsqueda: {res}")
                elif isinstance(res, list):
                    self.state.collected_docs.extend(res)
            
            # Fase 3: Validar fuentes (usamos el estado actualizado)
            val_result = self._validate_sources(self.state)
            self.state.validated_docs = val_result["validated_docs"]
            
            # Asegurar campo source_api en cada documento
            for doc in self.state.validated_docs:
                if "source_api" not in doc:
                    doc["source_api"] = doc.get("source", "API")
            
            # Fase 4: Exportar
            exp_result = self._export_results(self.state)
            
            return {
                "status": "success",
                "documents": self.state.validated_docs,
                "sources": self.state.validated_docs,
                "count": len(self.state.validated_docs),
                "total_collected": len(self.state.collected_docs),
                "databases_used": self.state.databases,
                "bibtex": exp_result.get("bibtex", ""),
                "csv": exp_result.get("csv", ""),
                "query_terms": interp_result.get("terms", [])
            }
            
        except Exception as e:
            self.state.error = str(e)
            self.state.status = "error"
            logger.error(f"Error en Bibliomancer: {e}")
            return {"status": "error", "error": str(e), "documents": [], "sources": []}

    async def search(
        self,
        query: str,
        max_results: int = 15,
        year_range: Optional[tuple] = None,
        databases: Optional[List[str]] = None
    ) -> BibliomancerSearchResult:
        """
        Método de búsqueda de literatura para bibliomancer.
        Retorna una lista enriquecida (BibliomancerSearchResult) compatible tanto
        con listas como con diccionarios que llaman a .get("sources").
        """
        filters: Dict[str, Any] = {}
        if max_results:
            filters["max_results"] = max_results
        if year_range and isinstance(year_range, (list, tuple)) and len(year_range) >= 2:
            filters["year_from"] = year_range[0]
            filters["year_to"] = year_range[1]

        res = await self.run(query=query, databases=databases, filters=filters)
        docs = res.get("documents", [])
        return BibliomancerSearchResult(docs, raw_dict=res)
    
    async def _search_semantic_scholar(self, session: aiohttp.ClientSession, query: str, filters: Dict) -> List[Dict]:
        """Búsqueda en Semantic Scholar API (pública, sin key)"""
        docs = []
        try:
            params = {
                "query": query,
                "fields": "title,authors,year,abstract,externalIds,publicationTypes,publicationDate,venue,citationCount,openAccessPdf",
                "limit": filters.get("max_results", 25)
            }
            if filters.get("year_from"):
                params["year"] = f"{filters['year_from']}-"
            
            async with session.get("https://api.semanticscholar.org/graph/v1/paper/search", params=params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for item in data.get("data", []):
                        authors = []
                        if item.get("authors"):
                            for a in item["authors"]:
                                authors.append(a.get("name", ""))
                        
                        pdf_url = None
                        if item.get("openAccessPdf"):
                            pdf_url = item["openAccessPdf"].get("url")
                        
                        docs.append({
                            "title": item.get("title", ""),
                            "authors": authors,
                            "year": item.get("year"),
                            "abstract": item.get("abstract", ""),
                            "doi": item.get("externalIds", {}).get("DOI"),
                            "url": f"https://www.semanticscholar.org/paper/{item.get('paperId', '')}",
                            "pdf_url": pdf_url,
                            "source": "semantic_scholar",
                            "type": item.get("publicationTypes", [""])[0] if item.get("publicationTypes") else "",
                            "citations": item.get("citationCount", 0),
                            "venue": item.get("venue", ""),
                            "publication_date": item.get("publicationDate", "")
                        })
                else:
                    logger.warning(f"Semantic Scholar status {resp.status}")
        except Exception as e:
            logger.error(f"Error en Semantic Scholar: {e}")
        return docs
    
    async def _search_arxiv(self, session: aiohttp.ClientSession, query: str, filters: Dict) -> List[Dict]:
        """Búsqueda en arXiv API (pública)"""
        docs = []
        try:
            params = {
                "search_query": f"all:{query}",
                "start": 0,
                "max_results": filters.get("max_results", 25),
                "sortBy": "relevance",
                "sortOrder": "descending"
            }
            
            async with session.get("https://export.arxiv.org/api/query", params=params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    root = ET.fromstring(text)
                    ns = {
                        "atom": "http://www.w3.org/2005/Atom",
                        "arxiv": "http://arxiv.org/schemas/atom"
                    }
                    
                    for entry in root.findall("atom:entry", ns):
                        title = entry.find("atom:title", ns)
                        title_text = title.text.strip().replace("\n", " ") if title is not None and title.text else ""
                        
                        authors = []
                        for author in entry.findall("atom:author", ns):
                            name = author.find("atom:name", ns)
                            if name is not None and name.text:
                                authors.append(name.text.strip())
                        
                        abstract = entry.find("atom:summary", ns)
                        abstract_text = abstract.text.strip().replace("\n", " ") if abstract is not None and abstract.text else ""
                        
                        published = entry.find("atom:published", ns)
                        year = None
                        if published is not None and published.text:
                            try:
                                year = int(published.text[:4])
                            except Exception:
                                pass
                        
                        link = entry.find("atom:id", ns)
                        url = link.text.strip() if link is not None and link.text else ""
                        
                        pdf_url = None
                        for link_el in entry.findall("atom:link", ns):
                            if link_el.get("title") == "pdf":
                                pdf_url = link_el.get("href")
                        
                        arxiv_id = url.split("/abs/")[-1] if "/abs/" in url else url
                        
                        docs.append({
                            "title": title_text,
                            "authors": authors,
                            "year": year,
                            "abstract": abstract_text,
                            "doi": None,
                            "url": url,
                            "pdf_url": pdf_url,
                            "source": "arxiv",
                            "type": "preprint",
                            "citations": 0,
                            "venue": "arXiv",
                            "publication_date": published.text[:10] if published is not None and published.text else ""
                        })
                else:
                    logger.warning(f"arXiv status {resp.status}")
        except Exception as e:
            logger.error(f"Error en arXiv: {e}")
        return docs
    
    async def _search_crossref(self, session: aiohttp.ClientSession, query: str, filters: Dict) -> List[Dict]:
        """Búsqueda en CrossRef API (pública)"""
        docs = []
        try:
            params = {
                "query": query,
                "rows": filters.get("max_results", 25),
                "select": "DOI,title,author,published-print,abstract,type,URL,link,is-referenced-by-count,container-title",
                "sort": "is-referenced-by-count",
                "order": "desc"
            }
            if filters.get("year_from"):
                params["filter"] = f"from-pub-date:{filters['year_from']}"
            
            async with session.get("https://api.crossref.org/works", params=params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for item in data.get("message", {}).get("items", []):
                        authors = []
                        for a in item.get("author", []):
                            given = a.get("given", "")
                            family = a.get("family", "")
                            name = f"{family}, {given}" if family else given
                            if name:
                                authors.append(name)
                        
                        title = item.get("title", [""])[0] if item.get("title") else ""
                        abstract = item.get("abstract", "")
                        if abstract:
                            # CrossRef a veces devuelve HTML entities; limpiar
                            abstract = abstract.replace("<jats:p>", "").replace("</jats:p>", " ").strip()
                        
                        year = None
                        pub_date = item.get("published-print", {}).get("date-parts", [[None]])[0]
                        if pub_date and pub_date[0]:
                            year = pub_date[0]
                        
                        doi = item.get("DOI")
                        url = item.get("URL", "")
                        
                        pdf_url = None
                        for link in item.get("link", []):
                            if link.get("intended-usage") == "text-mining" or link.get("content-type", "").startswith("application/pdf"):
                                pdf_url = link.get("URL")
                                break
                        
                        docs.append({
                            "title": title,
                            "authors": authors,
                            "year": year,
                            "abstract": abstract,
                            "doi": doi,
                            "url": url,
                            "pdf_url": pdf_url,
                            "source": "crossref",
                            "type": item.get("type", ""),
                            "citations": item.get("is-referenced-by-count", 0),
                            "venue": item.get("container-title", [""])[0] if item.get("container-title") else "",
                            "publication_date": str(pub_date[0]) if pub_date and pub_date[0] else ""
                        })
                else:
                    logger.warning(f"CrossRef status {resp.status}")
        except Exception as e:
            logger.error(f"Error en CrossRef: {e}")
        return docs
    
    async def _search_scielo(self, session: aiohttp.ClientSession, query: str, filters: Dict) -> List[Dict]:
        """Búsqueda en SciELO (API pública)"""
        docs = []
        try:
            params = {
                "q": query,
                "lang": "es",
                "count": filters.get("max_results", 25),
                "sort": "relevance"
            }
            async with session.get("https://api.scielo.org/search/", params=params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for item in data.get("results", []):
                        authors = []
                        for a in item.get("authors", []):
                            authors.append(a.get("full_name", ""))
                        docs.append({
                            "title": item.get("title", ""),
                            "authors": authors,
                            "year": item.get("year"),
                            "abstract": item.get("abstract", ""),
                            "doi": item.get("doi"),
                            "url": item.get("permalink", ""),
                            "pdf_url": item.get("pdf_url"),
                            "source": "scielo",
                            "type": item.get("type", ""),
                            "citations": item.get("citation_count", 0),
                            "venue": item.get("journal", ""),
                            "publication_date": item.get("publication_date", "")
                        })
                else:
                    logger.warning(f"SciELO status {resp.status}")
        except Exception as e:
            logger.error(f"Error en SciELO: {e}")
        return docs
    
    async def _search_redalyc(self, session: aiohttp.ClientSession, query: str, filters: Dict) -> List[Dict]:
        """Búsqueda en RedALyC (API pública)"""
        docs = []
        try:
            params = {
                "query": query,
                "limit": filters.get("max_results", 25)
            }
            async with session.get("https://www.redalyc.org/api/search", params=params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for item in data.get("results", []):
                        authors = []
                        for a in item.get("authors", []):
                            authors.append(a.get("name", ""))
                        docs.append({
                            "title": item.get("title", ""),
                            "authors": authors,
                            "year": item.get("year"),
                            "abstract": item.get("abstract", ""),
                            "doi": item.get("doi"),
                            "url": item.get("url", ""),
                            "pdf_url": item.get("pdf_url"),
                            "source": "redalyc",
                            "type": item.get("type", ""),
                            "citations": item.get("citations", 0),
                            "venue": item.get("journal", ""),
                            "publication_date": item.get("publication_date", "")
                        })
                else:
                    logger.warning(f"RedALyC status {resp.status}")
        except Exception as e:
            logger.error(f"Error en RedALyC: {e}")
        return docs
    
    async def _search_pubmed(self, session: aiohttp.ClientSession, query: str, filters: Dict) -> List[Dict]:
        """Búsqueda en PubMed (API E-utilities, pública)"""
        docs = []
        try:
            # Paso 1: Buscar IDs
            search_params = {
                "db": "pubmed",
                "term": query,
                "retmax": filters.get("max_results", 25),
                "retmode": "json",
                "sort": "relevance"
            }
            if filters.get("year_from"):
                search_params[filters.get("year_from")] = str(filters["year_from"])
            
            async with session.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi", params=search_params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    search_data = await resp.json()
                    id_list = search_data.get("esearchresult", {}).get("idlist", [])
                    
                    if not id_list:
                        return docs
                    
                    # Paso 2: Fetch detalles
                    fetch_params = {
                        "db": "pubmed",
                        "id": ",".join(id_list),
                        "retmode": "xml",
                        "rettype": "abstract"
                    }
                    async with session.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi", params=fetch_params, timeout=aiohttp.ClientTimeout(total=30)) as fetch_resp:
                        if fetch_resp.status == 200:
                            text = await fetch_resp.text()
                            root = ET.fromstring(text)
                            
                            for article in root.findall(".//PubmedArticle"):
                                medline = article.find(".//MedlineCitation")
                                if medline is None:
                                    continue
                                
                                article_data = medline.find("Article")
                                if article_data is None:
                                    continue
                                
                                title_el = article_data.find("ArticleTitle")
                                title = title_el.text if title_el is not None and title_el.text else ""
                                
                                abstract_el = article_data.find(".//AbstractText")
                                abstract = abstract_el.text if abstract_el is not None and abstract_el.text else ""
                                
                                authors = []
                                author_list = article_data.find("AuthorList")
                                if author_list is not None:
                                    for author in author_list.findall("Author"):
                                        last = author.find("LastName")
                                        first = author.find("ForeName")
                                        if last is not None and last.text:
                                            name = last.text
                                            if first is not None and first.text:
                                                name += f", {first.text}"
                                            authors.append(name)
                                
                                pmid = medline.find("PMID")
                                pmid_text = pmid.text if pmid is not None and pmid.text else ""
                                url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid_text}/" if pmid_text else ""
                                
                                year = None
                                pub_date = article_data.find(".//PubDate")
                                if pub_date is not None:
                                    year_el = pub_date.find("Year")
                                    if year_el is not None and year_el.text:
                                        year = int(year_el.text)
                                
                                journal_el = article_data.find("Journal/Title")
                                venue = journal_el.text if journal_el is not None and journal_el.text else ""
                                
                                docs.append({
                                    "title": title,
                                    "authors": authors,
                                    "year": year,
                                    "abstract": abstract,
                                    "doi": None,
                                    "url": url,
                                    "pdf_url": None,
                                    "source": "pubmed",
                                    "type": "journal article",
                                    "citations": 0,
                                    "venue": venue,
                                    "publication_date": str(year) if year else ""
                                })
                else:
                    logger.warning(f"PubMed search status {resp.status}")
        except Exception as e:
            logger.error(f"Error en PubMed: {e}")
        return docs
    
    def _export_bibtex(self, docs: List[Dict]) -> str:
        """Exporta documentos a formato BibTeX"""
        lines = []
        for i, doc in enumerate(docs):
            key = f"{doc.get('first_author', 'unknown').split(',')[0].lower() if doc.get('authors') else 'unknown'}{doc.get('year', '0000')}"
            entry_type = "article" if doc.get("type") == "journal article" else "misc"
            lines.append(f"@{entry_type}{{{key}{i},")
            lines.append(f"  title = {{{doc.get('title', '')}}},")
            if doc.get("authors"):
                authors_str = " and ".join(doc["authors"])
                lines.append(f"  author = {{{authors_str}}},")
            if doc.get("year"):
                lines.append(f"  year = {{{doc['year']}}},")
            if doc.get("venue"):
                lines.append(f"  journal = {{{doc['venue']}}},")
            if doc.get("url"):
                lines.append(f"  url = {{{doc['url']}}},")
            if doc.get("doi"):
                lines.append(f"  doi = {{{doc['doi']}}},")
            lines.append("}")
            lines.append("")
        return "\n".join(lines)
    
    def _export_csv(self, docs: List[Dict]) -> str:
        """Exporta documentos a CSV"""
        if not docs:
            return ""
        headers = ["title", "authors", "year", "source", "doi", "url", "type", "citations"]
        rows = [",".join(headers)]
        for doc in docs:
            row = []
            for h in headers:
                val = doc.get(h, "")
                if isinstance(val, list):
                    val = "; ".join(str(v) for v in val)
                val = str(val).replace(",", ";").replace("\n", " ")
                row.append(val)
            rows.append(",".join(row))
        return "\n".join(rows)
    
    async def search_scielo(self, query: str, filters: Dict = None) -> List[Dict]:
        """Búsqueda específica en Scielo"""
        session = await self._get_session()
        return await self._search_scielo(session, query, filters or {})
    
    async def search_redalyc(self, query: str, filters: Dict = None) -> List[Dict]:
        """Búsqueda específica en Redalyc"""
        session = await self._get_session()
        return await self._search_redalyc(session, query, filters or {})
    
    async def search_ebsco(self, query: str, filters: Dict = None) -> List[Dict]:
        """Búsqueda específica en EBSCO (no implementada - requiere API key institucional)"""
        logger.warning("EBSCO requiere API key institucional. Usa Semantic Scholar/arXiv como alternativa.")
        return []
    
    def get_search_summary(self) -> str:
        """Resumen de la última búsqueda"""
        return f"Bibliomancer: {len(self.state.validated_docs)} documentos válidos de {len(self.state.collected_docs)} recolectados"
