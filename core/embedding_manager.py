import logging
import os
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import asyncio
import uuid

# Para el modelo interno
from sentence_transformers import SentenceTransformer

# Para LiteLLM (Capa Genérica)
import litellm

# Para la configuración y secretos
from core.config import settings
from core.repositories.secret_repository import SecretRepository
from core.database import SessionLocal, Account # Necesario para obtener la configuración del usuario

logger = logging.getLogger(__name__)

# --- Interfaz Abstracta EmbeddingService ---
class EmbeddingService(ABC):
    """
    Interfaz abstracta para servicios de Embeddings.
    Define los métodos que cualquier implementación de Embedding debe proporcionar.
    """
    
    @abstractmethod
    async def aembed_query(self, text: str) -> List[float]:
        """
        Genera el embedding para una consulta de texto de forma asíncrona.
        """
        pass

    @abstractmethod
    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Genera embeddings para una lista de documentos de texto de forma asíncrona.
        """
        pass

# --- Implementación de KognitoInternalEmbeddingService ---
class KognitoInternalEmbeddingService(EmbeddingService):
    """
    Implementación de EmbeddingService para un modelo de embeddings interno
    cargado localmente (Sentence Transformers). Permanece para uso offline/económico.
    """
    
    _model: Optional[SentenceTransformer] = None
    DEFAULT_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"

    def __init__(self, model_name: str = DEFAULT_MODEL_NAME, use_fp16: bool = False):
        self.model_name = model_name
        self.use_fp16 = use_fp16
        if KognitoInternalEmbeddingService._model is None:
            logger.info(f"✨ Cargando modelo de embeddings interno: {self.model_name}...")
            try:
                KognitoInternalEmbeddingService._model = SentenceTransformer(self.model_name)
                if self.use_fp16:
                    KognitoInternalEmbeddingService._model.half()
                logger.info(f"✅ Modelo de embeddings interno cargado exitosamente.")
            except Exception as e:
                logger.error(f"❌ Error al cargar el modelo de embeddings interno: {e}")
                raise
        self._model = KognitoInternalEmbeddingService._model

    async def aembed_query(self, text: str) -> List[float]:
        if self._model is None: raise ValueError("Modelo no inicializado.")
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self._model.encode(text).tolist())

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        if self._model is None: raise ValueError("Modelo no inicializado.")
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self._model.encode(texts).tolist())

# --- Implementación de LiteLLMEmbeddingService (Capa Genérica) ---
class LiteLLMEmbeddingService(EmbeddingService):
    """
    Implementación UNIFICADA de EmbeddingService usando LiteLLM directamente.
    Compatible con OpenAI, Google (Gemini/Vertex), Azure, Anthropic, etc.
    """
    def __init__(self, model_name: str, api_key: Optional[str] = None, api_base: Optional[str] = None):
        self.model_name = model_name
        self.api_key = api_key
        self.api_base = api_base
        logger.info(f"✅ Servicio de Embeddings Genérico (LiteLLM Directo) inicializado para: {self.model_name}")

    async def aembed_query(self, text: str) -> List[float]:
        try:
            response = await litellm.aembedding(
                model=self.model_name,
                input=[text],
                api_key=self.api_key,
                api_base=self.api_base
            )
            # litellm devuelve un objeto con .data[0].embedding
            return response.data[0]['embedding']
        except Exception as e:
             logger.error(f"Error en aembed_query con LiteLLM: {e}")
             raise

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        try:
            response = await litellm.aembedding(
                model=self.model_name,
                input=texts,
                api_key=self.api_key,
                api_base=self.api_base
            )
            # Extraer lista de embeddings
            return [item['embedding'] for item in response.data]
        except Exception as e:
             logger.error(f"Error en aembed_documents con LiteLLM: {e}")
             raise

# --- EmbeddingServiceFactory ---
class EmbeddingServiceFactory:
    """
    Fábrica para obtener instancias de EmbeddingService.
    """
    
    _instances: Dict[str, EmbeddingService] = {}
    
    @staticmethod
    async def get_service(
        provider: str, 
        model_name: Optional[str] = None,
        api_key_name: Optional[str] = None,
        api_base: Optional[str] = None,
        account_id: Optional[uuid.UUID] = None
    ) -> EmbeddingService:
        """
        Obtiene una instancia del servicio de embeddings.
        """
        provider_lower = provider.lower()
        instance_key = f"{provider_lower}-{model_name}-{api_base}-{api_key_name}-{account_id}"
        
        if instance_key not in EmbeddingServiceFactory._instances:
            api_key = None
            if api_key_name and account_id:
                async with SessionLocal() as db:
                    secret_repo = SecretRepository(db)
                    api_key = await secret_repo.get_decrypted_secret(account_id, api_key_name)
            
            if provider_lower == "kognito-internal":
                if not model_name:
                    model_name = KognitoInternalEmbeddingService.DEFAULT_MODEL_NAME
                EmbeddingServiceFactory._instances[instance_key] = KognitoInternalEmbeddingService(model_name=model_name)
            
            elif provider_lower in ["openai", "google", "ollama", "gemini", "vertex-ai", "litellm"]:
                # Caso Genérico: Todos estos ahora pasan por LiteLLM
                if not model_name:
                    raise ValueError(f"model_name es requerido para el proveedor {provider}.")
                
                # FIX: Si es Ollama local, evitamos enviar API Key para prevenir errores 401 (unauthorized)
                # LiteLLM a veces intenta usar llaves del entorno si se pasan como None, 
                # pero si las pasamos vacías explícitamente suele ser más seguro para local.
                effective_api_key = api_key
                if provider_lower == "ollama" and not api_base:
                    effective_api_key = None # Opcionalmente "" si None no funciona
                
                # Para Google Vertex, a veces se requiere el project_id en el api_base o ENV
                # Pero LiteLLM suele manejarlo automáticamente con las credenciales de entorno.
                EmbeddingServiceFactory._instances[instance_key] = LiteLLMEmbeddingService(
                    model_name=model_name, 
                    api_key=effective_api_key, 
                    api_base=api_base
                )
            else:
                # Si no es interno, intentamos usarlo como un string de modelo directo de LiteLLM
                logger.info(f"Intentando usar proveedor desconocido '{provider}' como modelo directo de LiteLLM")
                EmbeddingServiceFactory._instances[instance_key] = LiteLLMEmbeddingService(
                    model_name=model_name or provider, 
                    api_key=api_key, 
                    api_base=api_base
                )
                
        return EmbeddingServiceFactory._instances[instance_key]

# Instancia global del servicio de embeddings por defecto
_default_embedding_service: Optional[EmbeddingService] = None

async def get_embedding_service(
    provider: Optional[str] = None,
    model_name: Optional[str] = None,
    api_key_name: Optional[str] = None,
    api_base: Optional[str] = None,
    account_id: Optional[uuid.UUID] = None
) -> EmbeddingService:
    """
    Obtiene una instancia del servicio de embeddings, usando la configuración del usuario
    o el servicio por defecto si no se especifica.
    """
    global _default_embedding_service

    # Si no se especifica un proveedor, usar el por defecto
    if not provider:
        if _default_embedding_service is None:
            # Inicializar el servicio interno por defecto si no hay otro configurado globalmente
            logger.info("Inicializando servicio de embeddings interno por defecto.")
            _default_embedding_service = await EmbeddingServiceFactory.get_service(
                provider="kognito-internal",
                model_name=KognitoInternalEmbeddingService.DEFAULT_MODEL_NAME
            )
        return _default_embedding_service
    
    # Si se especifica un proveedor, obtenerlo a través de la fábrica
    return await EmbeddingServiceFactory.get_service(
        provider=provider,
        model_name=model_name,
        api_key_name=api_key_name,
        api_base=api_base,
        account_id=account_id
    )

# Funciones de conveniencia para el resto del código
async def aembed_query(
    text: str,
    provider: Optional[str] = None,
    model_name: Optional[str] = None,
    api_key_name: Optional[str] = None,
    api_base: Optional[str] = None,
    account_id: Optional[uuid.UUID] = None
) -> List[float]:
    """
    Genera el embedding para una consulta de texto.
    """
    service = await get_embedding_service(provider, model_name, api_key_name, api_base, account_id)
    return await service.aembed_query(text)

async def aembed_documents(
    texts: List[str],
    provider: Optional[str] = None,
    model_name: Optional[str] = None,
    api_key_name: Optional[str] = None,
    api_base: Optional[str] = None,
    account_id: Optional[uuid.UUID] = None
) -> List[List[float]]:
    """
    Genera embeddings para una lista de documentos de texto.
    """
    service = await get_embedding_service(provider, model_name, api_key_name, api_base, account_id)
    return await service.aembed_documents(texts)
