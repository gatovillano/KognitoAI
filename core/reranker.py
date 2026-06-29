import logging
import uuid
import json
import os
import httpx
import torch
from typing import List, Optional, Dict, Any
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from sqlalchemy import select

from core.database import SessionLocal, Account, SystemSettings
from utils.db_session import DBSession
from core.repositories.secret_repository import SecretRepository
from core.config import settings

logger = logging.getLogger(__name__)

SYSTEM_ACCOUNT_ID = uuid.UUID("00000000-0000-0000-0000-000000000000")

_http_client = None

def get_http_client():
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(8.0, connect=3.0),
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
        )
    return _http_client

async def ensure_system_account(db):
    account = await db.get(Account, SYSTEM_ACCOUNT_ID)
    if not account:
        account = Account(
            id=SYSTEM_ACCOUNT_ID,
            name="System",
            email="system@kognito.ai",
            is_admin=True,
            is_active=True
        )
        db.add(account)
        await db.commit()

class BaseReranker:
    async def rerank(self, query: str, documents: list, top_n: Optional[int] = None, threshold: Optional[float] = None) -> list:
        raise NotImplementedError()

class LocalReranker(BaseReranker):
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model_name = model_name
        self._model = None
        self._tokenizer = None

    def _load_model(self):
        if self._model is not None:
            return
        try:
            logger.info(f"Cargando modelo local de reranking: {self.model_name}...")
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self._model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
            self._model.eval()
            logger.info("✅ Modelo local de reranking cargado exitosamente.")
        except Exception as e:
            logger.error(f"❌ Error al cargar el modelo local de reranking {self.model_name}: {e}", exc_info=True)
            self._model = None
            self._tokenizer = None

    async def rerank(self, query: str, documents: list, top_n: Optional[int] = None, threshold: Optional[float] = None) -> list:
        self._load_model()
        if not self._model or not self._tokenizer:
            logger.warning("Modelo local de reranking no cargado. Saltando reranking.")
            return documents

        if not documents:
            return []

        final_top_n = top_n if top_n is not None else settings.reranker_top_n
        final_threshold = threshold if threshold is not None else settings.reranker_threshold
        if final_threshold == 0.0:
            final_threshold = -10.0

        document_contents = [doc.page_content for doc in documents]
        features = self._tokenizer([query] * len(document_contents), document_contents, padding=True, truncation=True, return_tensors='pt')

        with torch.no_grad():
            scores = self._model(**features).logits.squeeze().tolist()

        if not isinstance(scores, list):
            scores = [scores]

        for doc, score in zip(documents, scores):
            doc.metadata['rerank_score'] = score

        # 1. Ordenar por score
        reranked_documents = sorted(documents, key=lambda x: x.metadata['rerank_score'], reverse=True)
        
        # 2. Filtrar por umbral de relevancia (Thresholding)
        filtered_documents = [doc for doc in reranked_documents if doc.metadata['rerank_score'] >= final_threshold]
        
        # 3. Limitar a Top N (aumentado a 20 por compatibilidad con la implementación previa)
        limit = max(20, final_top_n)
        final_documents = filtered_documents[:limit]
        
        logger.info(f"✨ Reranking local: Recibidos {len(documents)}, filtrados {len(filtered_documents)}, devueltos {len(final_documents)} (Umbral: {final_threshold}, Top N: {limit})")
        if final_documents:
            top_scores = [doc.metadata['rerank_score'] for doc in final_documents[:3]]
            logger.info(f"📊 Top 3 scores post-filtro local: {[round(s, 4) for s in top_scores]}")
        
        return final_documents

class CloudReranker(BaseReranker):
    _cache = {}
    _cache_limit = 2000

    def __init__(self, provider: str, model: str, api_base: Optional[str] = None, api_key: Optional[str] = None):
        self.provider = provider.lower()
        self.model = model
        # Default api_base if not specified
        if not api_base:
            if self.provider == "openrouter":
                api_base = "https://openrouter.ai/api/v1"
            elif self.provider == "cohere":
                api_base = "https://api.cohere.com/v1"
            else:
                api_base = ""
        self.api_base = api_base
        self.api_key = api_key

    async def rerank(self, query: str, documents: list, top_n: Optional[int] = None, threshold: Optional[float] = None) -> list:
        if not documents:
            return []

        if len(documents) == 1:
            documents[0].metadata['rerank_score'] = documents[0].metadata.get('rerank_score', 1.0)
            return documents

        # Determine endpoint URL
        url = self.api_base
        if not url.endswith("/rerank"):
            url = url.rstrip("/") + "/rerank"

        # Buscar en cache local
        cached_results = {}
        uncached_docs = []
        uncached_indices = []

        for i, doc in enumerate(documents):
            cache_key = (self.provider, self.model, query, doc.page_content)
            if cache_key in self._cache:
                cached_results[i] = self._cache[cache_key]
            else:
                uncached_docs.append(doc)
                uncached_indices.append(i)

        final_top_n = top_n if top_n is not None else settings.reranker_top_n

        if not uncached_docs:
            logger.info(f"🎯 Reranker Cache HIT completo para {len(documents)} documentos.")
            for i, doc in enumerate(documents):
                doc.metadata['rerank_score'] = cached_results[i]
        else:
            if len(uncached_docs) < len(documents):
                logger.info(f"🎯 Reranker Cache HIT parcial: {len(documents) - len(uncached_docs)} recuperados de caché, {len(uncached_docs)} pendientes.")

            headers = {
                "Content-Type": "application/json"
            }
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            headers["HTTP-Referer"] = "https://kognito.ai"
            headers["X-Title"] = "KognitoAI"

            payload = {
                "model": self.model,
                "query": query,
                "documents": [doc.page_content for doc in uncached_docs],
                "top_n": final_top_n
            }

            try:
                logger.info(f"🌐 Enviando petición de reranking en la nube a {url} usando modelo {self.model} ({len(uncached_docs)} docs)...")
                client = get_http_client()
                response = await client.post(url, headers=headers, json=payload)
                if response.status_code != 200:
                    logger.error(f"❌ Petición de rerank en la nube falló con código {response.status_code}: {response.text}")
                    raise httpx.HTTPStatusError(f"HTTP Error {response.status_code}", request=response.request, response=response)

                data = response.json()
                results = data.get("results", [])
                
                # Mapear los scores a los documentos
                score_map = {}
                for item in results:
                    idx = item.get("index")
                    score = item.get("relevance_score")
                    if idx is not None and score is not None:
                        score_map[idx] = score

                # Guardar en cache y asignar
                if len(self._cache) > self._cache_limit:
                    self._cache.clear()

                for i, doc in enumerate(uncached_docs):
                    score = score_map.get(i, 0.0)
                    doc.metadata['rerank_score'] = score
                    
                    cache_key = (self.provider, self.model, query, doc.page_content)
                    self._cache[cache_key] = score

                # Asignar caché a los que ya estaban cacheados
                for i, doc in enumerate(documents):
                    if i in cached_results:
                        doc.metadata['rerank_score'] = cached_results[i]

            except Exception as e:
                logger.error(f"❌ Error en CloudReranker: {e}. Lanzando excepción para activar fallback.")
                raise e

        # 1. Ordenar por score
        reranked_documents = sorted(documents, key=lambda x: x.metadata.get('rerank_score', 0.0), reverse=True)
        
        # 2. Filtrar por umbral de relevancia (Thresholding)
        final_threshold = threshold if threshold is not None else settings.reranker_threshold
        filtered_documents = [doc for doc in reranked_documents if doc.metadata.get('rerank_score', 0.0) >= final_threshold]
        
        # 3. Limitar a Top N
        limit = max(20, final_top_n)
        final_documents = filtered_documents[:limit]
        
        logger.info(f"✨ Reranking nube completado: Recibidos {len(documents)}, filtrados {len(filtered_documents)}, devueltos {len(final_documents)}")
        if final_documents:
            top_scores = [doc.metadata.get('rerank_score', 0.0) for doc in final_documents[:3]]
            logger.info(f"📊 Top 3 scores post-filtro nube: {[round(s, 4) for s in top_scores]}")
        
        return final_documents

class Reranker:
    _local_reranker = None

    def __init__(self):
        pass

    @classmethod
    def get_local_reranker(cls, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        if cls._local_reranker is None:
            cls._local_reranker = LocalReranker(model_name)
        return cls._local_reranker

    async def rerank(self, query: str, documents: list, top_n: Optional[int] = None, threshold: Optional[float] = None, account_id: Optional[str] = None) -> list:
        provider = "local"
        model = "cross-encoder/ms-marco-MiniLM-L-6-v2"
        api_base = None
        api_key = None

        # 1. Buscar en la cuenta del usuario
        if account_id:
            try:
                async with DBSession(SessionLocal) as db:
                    account = await db.get(Account, uuid.UUID(account_id) if isinstance(account_id, str) else account_id)
                    if account and account.reranker_provider:
                        provider = account.reranker_provider
                        model = account.reranker_model or model
                        api_base = account.reranker_api_base
                        
                        # Si es nube, buscar la API key en secretos
                        if provider.lower() != "local":
                            secret_repo = SecretRepository(db)
                            key_to_search = f"{provider.upper().replace('-', '_')}_API_KEY"
                            api_key = await secret_repo.get_decrypted_secret(account.id, key_to_search)
                            
                            # Fallback a global
                            if not api_key:
                                await ensure_system_account(db)
                                api_key = await secret_repo.get_decrypted_secret(SYSTEM_ACCOUNT_ID, key_to_search)
            except Exception as e:
                logger.error(f"Error al cargar configuración de reranker para el usuario {account_id}: {e}")

        # 2. Si no es personalizado por usuario, intentar cargar de global settings (SystemSettings)
        if provider == "local" or not provider:
            try:
                async with DBSession(SessionLocal) as db:
                    result = await db.execute(select(SystemSettings).where(SystemSettings.key == "global_llm_settings"))
                    row = result.scalar_one_or_none()
                    if row and row.value:
                        global_settings = json.loads(row.value)
                        if global_settings.get("reranker_provider"):
                            provider = global_settings.get("reranker_provider")
                            model = global_settings.get("reranker_model") or model
                            api_base = global_settings.get("reranker_api_base")
                            
                            # Si es nube, buscar la API key en secretos
                            if provider.lower() != "local":
                                secret_repo = SecretRepository(db)
                                key_to_search = f"{provider.upper().replace('-', '_')}_API_KEY"
                                await ensure_system_account(db)
                                api_key = await secret_repo.get_decrypted_secret(SYSTEM_ACCOUNT_ID, key_to_search)
            except Exception as e:
                logger.error(f"Error al cargar configuración global de reranker de la DB: {e}")

        # 3. Si sigue sin estar definido o es local por defecto, usar settings globales de config.py
        if not provider or provider == "local":
            provider = settings.reranker_provider
            model = settings.reranker_model_name
            api_base = settings.reranker_api_base
            # Si se especificó un proveedor de nube en settings globales, buscar la API key en variables de entorno o secretos globales
            if provider.lower() != "local":
                api_key = os.environ.get(f"{provider.upper().replace('-', '_')}_API_KEY")
                if not api_key:
                    try:
                        async with DBSession(SessionLocal) as db:
                            secret_repo = SecretRepository(db)
                            key_to_search = f"{provider.upper().replace('-', '_')}_API_KEY"
                            await ensure_system_account(db)
                            api_key = await secret_repo.get_decrypted_secret(SYSTEM_ACCOUNT_ID, key_to_search)
                    except Exception as e:
                        logger.error(f"Error al buscar API key global para {provider}: {e}")

        logger.info(f"🎯 Usando reranker provider={provider}, model={model}")

        if provider.lower() == "local":
            local_reranker = self.get_local_reranker(model)
            return await local_reranker.rerank(query, documents, top_n=top_n, threshold=threshold)
        else:
            cloud_reranker = CloudReranker(provider=provider, model=model, api_base=api_base, api_key=api_key)
            try:
                return await cloud_reranker.rerank(query, documents, top_n=top_n, threshold=threshold)
            except Exception as e:
                logger.error(f"Fallo en reranker en la nube. Usando fallback local. Error: {e}")
                local_reranker = self.get_local_reranker()
                try:
                    return await local_reranker.rerank(query, documents, top_n=top_n, threshold=threshold)
                except Exception as local_err:
                    logger.error(f"Fallo también el fallback local: {local_err}. Se retornarán documentos sin rerankear.")
                    return documents

# Singleton para compatibilidad con importaciones existentes
reranker = Reranker()
