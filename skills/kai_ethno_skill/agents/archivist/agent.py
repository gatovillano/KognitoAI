"""
Archivist Agent - Guardián de la Memoria
Agente especializado en gestión del conocimiento colectivo
"""

import asyncio
import json
import logging
import hashlib
from typing import Dict, List, Any, Optional
from datetime import datetime
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ArchivistState(BaseModel):
    """Estado del agente Archivist"""
    documents: List[Dict[str, Any]] = Field(default_factory=list)
    indexed_documents: List[str] = Field(default_factory=list)
    metadata_index: Dict[str, Any] = Field(default_factory=dict)
    backup_status: Dict[str, Any] = Field(default_factory=dict)
    optimization_report: Optional[Dict[str, Any]] = None
    status: str = "idle"


class ArchivistAgent:
    """
    Agente Archivist - Especialista en gestión de conocimiento
    
    Capacidades:
    - Indexación semántica de documentos
    - Detección de duplicados
    - Backup incremental
    - Optimización de almacenamiento
    - trazabilidad de versiones
    """
    
    name = "archivist"
    description = "Guardián de la Memoria - Gestión del conocimiento colectivo"
    
    def __init__(self, llm_service: Any = None, storage_path: str = "./output/archive"):
        self.llm = llm_service
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True) if 'os' in globals() else None
        self.graph = self._build_graph()
        self.state = ArchivistState()
        self.document_store: Dict[str, Dict] = {}
        self.metadata_store: Dict[str, Dict] = {}
    
    def _build_graph(self) -> StateGraph:
        """Construye el grafo de LangGraph para el flujo del agente"""
        
        def ingest_documents(state: ArchivistState) -> Dict[str, Any]:
            """Ingiere y valida documentos"""
            ingested = []
            for doc in state.documents:
                doc_id = self._generate_doc_id(doc)
                doc["_id"] = doc_id
                doc["ingested_at"] = datetime.now().isoformat()
                ingested.append(doc)
            return {"status": "ingested", "ingested_docs": ingested}
        
        def normalize_metadata(state: ArchivistState) -> Dict[str, Any]:
            """Normaliza metadatos a formato estándar"""
            normalized = []
            for doc in state.documents:
                norm = {
                    "_id": doc.get("_id"),
                    "title": doc.get("title", "").strip(),
                    "authors": [a.strip() for a in doc.get("authors", []) if a],
                    "year": doc.get("year"),
                    "source": doc.get("source", "").strip().lower(),
                    "type": doc.get("type", "").strip().lower(),
                    "doi": doc.get("doi", "").strip() if doc.get("doi") else None,
                    "url": doc.get("url", "").strip() if doc.get("url") else None,
                    "abstract_length": len(doc.get("abstract", "")),
                    "word_count": len(doc.get("abstract", "").split()),
                    "language": self._detect_language(doc.get("title", "") + " " + doc.get("abstract", "")),
                    "normalized_at": datetime.now().isoformat()
                }
                normalized.append(norm)
            return {"status": "normalized", "normalized_docs": normalized}
        
        def index_documents(state: ArchivistState) -> Dict[str, Any]:
            """Indexa documentos en almacenamiento local"""
            indexed = []
            for doc in state.documents:
                doc_id = doc.get("_id")
                if not doc_id:
                    continue
                
                # Almacenar documento completo
                self.document_store[doc_id] = doc
                
                # Indexar metadatos
                self.metadata_store[doc_id] = {
                    "title": doc.get("title", ""),
                    "authors": doc.get("authors", []),
                    "year": doc.get("year"),
                    "source": doc.get("source"),
                    "type": doc.get("type"),
                    "doi": doc.get("doi"),
                    "abstract_length": len(doc.get("abstract", "")),
                    "indexed_at": datetime.now().isoformat()
                }
                
                indexed.append(doc_id)
            
            # Persistir en disco
            self._persist()
            
            return {"status": "indexed", "indexed_count": len(indexed), "indexed_ids": indexed}
        
        def detect_duplicates(state: ArchivistState) -> Dict[str, Any]:
            """Detecta duplicados por DOI, título similar o URL"""
            seen_dois = {}
            seen_titles = {}
            duplicates = []
            unique = []
            
            for doc in state.documents:
                doc_id = doc.get("_id")
                doi = doc.get("doi")
                title = doc.get("title", "").lower().strip()
                
                is_duplicate = False
                dup_reason = None
                
                # Chequear DOI
                if doi:
                    if doi in seen_dois:
                        is_duplicate = True
                        dup_reason = f"duplicate_doi:{seen_dois[doi]}"
                    else:
                        seen_dois[doi] = doc_id
                
                # Chequear título similar (si no hay DOI o no es duplicado por DOI)
                if not is_duplicate and title:
                    # Buscar títulos muy similares (simplificado: primeros 50 caracteres)
                    title_key = title[:50]
                    if title_key in seen_titles:
                        is_duplicate = True
                        dup_reason = f"duplicate_title:{seen_titles[title_key]}"
                    else:
                        seen_titles[title_key] = doc_id
                
                if is_duplicate:
                    duplicates.append({
                        "doc_id": doc_id,
                        "reason": dup_reason,
                        "title": doc.get("title", "")[:50]
                    })
                else:
                    unique.append(doc)
            
            return {"status": "duplicates_detected", "duplicates": duplicates, "unique_count": len(unique)}
        
        def backup_knowledge(state: ArchivistState) -> Dict[str, Any]:
            """Genera backup del conocimiento"""
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_info = {
                "timestamp": timestamp,
                "document_count": len(self.document_store),
                "metadata_count": len(self.metadata_store),
                "backup_file": os.path.join(self.storage_path, f"backup_{timestamp}.json") if 'os' in globals() else f"./output/archive/backup_{timestamp}.json",
                "status": "completed"
            }
            
            # Guardar backup
            backup_data = {
                "documents": self.document_store,
                "metadata": self.metadata_store,
                "created_at": timestamp
            }
            try:
                with open(backup_info["backup_file"], "w", encoding="utf-8") as f:
                    json.dump(backup_data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"Error en backup: {e}")
                backup_info["status"] = "error"
                backup_info["error"] = str(e)
            
            return {"status": "backed_up", "backup_info": backup_info}
        
        workflow = StateGraph(ArchivistState)
        
        workflow.add_node("ingest", ingest_documents)
        workflow.add_node("normalize", normalize_metadata)
        workflow.add_node("index", index_documents)
        workflow.add_node("duplicates", detect_duplicates)
        workflow.add_node("backup", backup_knowledge)
        
        workflow.set_entry_point("ingest")
        workflow.add_edge("ingest", "normalize")
        workflow.add_edge("normalize", "index")
        workflow.add_edge("index", "duplicates")
        workflow.add_edge("duplicates", "backup")
        workflow.add_edge("backup", END)
        
        return workflow.compile()
    
    async def run(self, documents: Any = None, **kwargs: Any) -> Dict[str, Any]:
        """Ejecuta el agente con documentos para gestionar"""
        if isinstance(documents, dict):
            doc_list = documents.get("documents") or documents.get("sources") or [documents]
        elif isinstance(documents, list):
            doc_list = []
            for item in documents:
                if isinstance(item, dict):
                    doc_list.append(item)
                elif isinstance(item, list):
                    doc_list.extend([i for i in item if isinstance(i, dict)])
        elif documents is not None:
            doc_list = [documents]
        else:
            doc_list = []

        self.state.documents = doc_list
        self.state.status = "running"
        
        try:
            result = await self.graph.ainvoke(self.state)
            self.state = ArchivistState(**result)
            return {
                "status": "success",
                "indexed_count": len(self.state.indexed_documents),
                "metadata_index": self.state.metadata_index,
                "backup_status": self.state.backup_status,
                "duplicates": result.get("duplicates", [])
            }
        except Exception as e:
            self.state.status = "error"
            logger.error(f"Error en Archivist: {e}")
            return {"status": "error", "error": str(e)}
    
    def _generate_doc_id(self, doc: Dict) -> str:
        """Genera ID único para documento"""
        title = doc.get("title", "")
        authors = "".join(doc.get("authors", []))
        year = str(doc.get("year", ""))
        raw = f"{title}{authors}{year}"
        return hashlib.md5(raw.encode()).hexdigest()[:12]
    
    def _detect_language(self, text: str) -> str:
        """Detección de idioma simple basada en caracteres comunes"""
        if not text:
            return "unknown"
        
        text_lower = text.lower()
        
        # Palabras comunes por idioma
        spanish_words = {"el", "la", "los", "las", "un", "una", "de", "del", "y", "en", "para", "por", "con", "estudio", "análisis", "desarrollo"}
        english_words = {"the", "and", "for", "with", "this", "that", "study", "analysis", "development", "research"}
        portuguese_words = {"o", "a", "os", "as", "um", "uma", "de", "do", "e", "em", "para", "por", "com", "estudo", "análise", "desenvolvimento"}
        
        counts = {"es": 0, "en": 0, "pt": 0}
        
        for word in spanish_words:
            if word in text_lower:
                counts["es"] += 1
        for word in english_words:
            if word in text_lower:
                counts["en"] += 1
        for word in portuguese_words:
            if word in text_lower:
                counts["pt"] += 1
        
        if max(counts.values()) == 0:
            return "unknown"
        
        return max(counts, key=counts.get)
    
    def _persist(self):
        """Persiste almacenamiento en disco"""
        try:
            import os
            os.makedirs(self.storage_path, exist_ok=True)
            
            with open(os.path.join(self.storage_path, "documents.json"), "w", encoding="utf-8") as f:
                json.dump(self.document_store, f, ensure_ascii=False, indent=2, default=str)
            
            with open(os.path.join(self.storage_path, "metadata.json"), "w", encoding="utf-8") as f:
                json.dump(self.metadata_store, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error persistiendo: {e}")
    
    def search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Búsqueda simple en índice de metadatos"""
        results = []
        query_lower = query.lower()
        
        for doc_id, meta in self.metadata_store.items():
            score = 0.0
            title = meta.get("title", "").lower()
            
            # Coincidencia en título
            if query_lower in title:
                score += 0.5
            
            # Coincidencia en palabras del título
            query_words = query_lower.split()
            for word in query_words:
                if word in title:
                    score += 0.1
            
            if score > 0:
                results.append({
                    "doc_id": doc_id,
                    "score": score,
                    "title": meta.get("title"),
                    "year": meta.get("year"),
                    "source": meta.get("source")
                })
        
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]
    
    def get_stats(self) -> Dict[str, Any]:
        """Estadísticas del archivo"""
        year_dist = defaultdict(int)
        source_dist = defaultdict(int)
        type_dist = defaultdict(int)
        
        for meta in self.metadata_store.values():
            year = meta.get("year")
            if year:
                year_dist[year] += 1
            source_dist[meta.get("source", "unknown")] += 1
            type_dist[meta.get("type", "unknown")] += 1
        
        return {
            "total_documents": len(self.document_store),
            "indexed_documents": len(self.metadata_store),
            "year_distribution": dict(sorted(year_dist.items())),
            "source_distribution": dict(source_dist),
            "type_distribution": dict(type_dist),
            "storage_path": self.storage_path
        }
    
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Recupera documento por ID"""
        return self.document_store.get(doc_id)
    
    def get_metadata(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Recupera metadatos por ID"""
        return self.metadata_store.get(doc_id)
