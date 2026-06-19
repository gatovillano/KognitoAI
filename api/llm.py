# api/llm.py

import logging
import httpx
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
from core.config import settings
from core.repositories.secret_repository import SecretRepository
from core.database import SessionLocal, Account
from utils.security import get_current_account_id
import uuid
import os

logger = logging.getLogger(__name__)

router = APIRouter()

# Caché simple en memoria para evitar llamadas excesivas
_models_cache: Dict[str, Dict[str, Any]] = {}
import time

CACHE_TTL = 3600  # 1 hora


async def get_user_api_key(account_id: str, provider: str) -> Optional[str]:
    """
    Obtiene la API key del usuario desde los secretos encriptados.
    """
    try:
        async with SessionLocal() as db:
            repo = SecretRepository(db)
            key_name = f"{provider.upper()}_API_KEY"
            api_key = await repo.get_decrypted_secret(uuid.UUID(account_id), key_name)

            if not api_key and provider.lower() in ["gemini", "google"]:
                api_key = await repo.get_decrypted_secret(uuid.UUID(account_id), "GOOGLE_API_KEY")

            if api_key:
                if not api_key.isascii():
                    logger.warning(f"API key for {provider} contains non-ASCII characters. Stripping them.")
                    api_key = api_key.encode('ascii', 'ignore').decode('ascii')

            return api_key
    except Exception as e:
        logger.error(f"Error al obtener API key para {provider}: {e}")
        return None


async def get_user_api_base(account_id: str) -> Optional[str]:
    """
    Obtiene la API base personalizada del usuario.
    """
    try:
        async with SessionLocal() as db:
            account = await db.get(Account, uuid.UUID(account_id))
            if account:
                return account.llm_api_base
    except Exception as e:
        logger.error(f"Error al obtener API base para usuario {account_id}: {e}")
    return None


@router.get("/llm/models/{provider}", response_model=List[Dict[str, Any]])
async def get_provider_models(
    provider: str, 
    api_base: Optional[str] = None,
    refresh: bool = False,
    current_account_id: str = Depends(get_current_account_id)
):
    """
    Obtiene la lista de modelos disponibles directamente desde el proveedor.
    Permite opcionalmente pasar una api_base personalizada (útil para previsualización antes de guardar).
    """
    provider = provider.lower()
    now = time.time()
    
    # Verificar caché (solo si no se pide refresh)
    if not refresh and provider in _models_cache:
        cache_entry = _models_cache[provider]
        # Para Ollama/local, el cache es mucho más corto (5 min) para detectar cambios locales
        ttl = 300 if provider == "ollama" else CACHE_TTL
        if now - cache_entry["timestamp"] < ttl:
            logger.info(f"Retornando modelos de {provider} desde caché.")
            return cache_entry["models"]

    models = []
    
    try:
        # Prioridad de API Base:
        # 1. Parámetro de la función (para previsualización)
        # 2. Base de datos del usuario
        # 3. Configuración global (.env LLM_API_BASE)
        # 4. Configuración específica (.env OLLAMA_API_URL para Ollama)
        user_api_key = await get_user_api_key(current_account_id, provider)
        user_api_base = api_base if api_base is not None else await get_user_api_base(current_account_id)
        
        # Proveedores específicos: llamadas directas a sus APIs
        if provider == "openrouter":
            async with httpx.AsyncClient() as client:
                headers = {}
                if user_api_key:
                    headers["Authorization"] = f"Bearer {user_api_key}"
                elif settings.openrouter_api_key:
                    headers["Authorization"] = f"Bearer {settings.openrouter_api_key}"
                
                response = await client.get(
                    "https://openrouter.ai/api/v1/models", 
                    headers=headers, 
                    timeout=15.0
                )
                response.raise_for_status()
                data = response.json()
                raw_models = data.get("data", [])
                
                for m in raw_models:
                    models.append({
                        "id": m.get("id"),
                        "name": m.get("name") or m.get("id"),
                        "description": m.get("description", ""),
                        "context_length": m.get("context_length"),
                        "pricing": m.get("pricing", {})
                    })
                logger.info(f"Obtenidos {len(models)} modelos de OpenRouter")

        elif provider == "openai":
            api_key = user_api_key or settings.openai_api_key
            if api_key:
                async with httpx.AsyncClient() as client:
                    headers = {"Authorization": f"Bearer {api_key}"}
                    response = await client.get(
                        "https://api.openai.com/v1/models", 
                        headers=headers, 
                        timeout=15.0
                    )
                    response.raise_for_status()
                    data = response.json()
                    raw_models = data.get("data", [])
                    
                    for m in raw_models:
                        model_id = m.get("id")
                        if any(x in model_id.lower() for x in ["gpt", "chat"]):
                            models.append({
                                "id": f"openai/{model_id}", 
                                "name": model_id,
                                "context_length": m.get("context_length"),
                                "pricing": m.get("pricing", {})
                            })
                    logger.info(f"Obtenidos {len(models)} modelos de OpenAI")

        elif provider == "anthropic":
            api_key = user_api_key
            if not api_key:
                api_key = os.getenv("ANTHROPIC_API_KEY")
            
            if api_key:
                async with httpx.AsyncClient() as client:
                    headers = {
                        "Authorization": f"Bearer {api_key}",
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01"
                    }
                    response = await client.get(
                        "https://api.anthropic.com/v1/models",
                        headers=headers,
                        timeout=15.0
                    )
                    if response.status_code == 200:
                        data = response.json()
                        for m in data.get("data", []):
                            models.append({
                                "id": f"anthropic/{m.get('id')}",
                                "name": m.get('display_name', m.get('id')),
                                "description": m.get('description', ''),
                                "context_length": m.get('context_length'),
                            })
                    elif response.status_code == 404:
                        # Anthropic no tiene endpoint público para modelos
                        models = [
                            {"id": "anthropic/claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet"},
                            {"id": "anthropic/claude-3-5-sonnet-20240620", "name": "Claude 3.5 Sonnet (Jun 2024)"},
                            {"id": "anthropic/claude-3-opus-20240229", "name": "Claude 3 Opus"},
                            {"id": "anthropic/claude-3-haiku-20240307", "name": "Claude 3 Haiku"},
                        ]
                logger.info(f"Obtenidos {len(models)} modelos de Anthropic")

        elif provider in ["google", "gemini"]:
            api_key = user_api_key or settings.google_api_key
            
            if api_key:
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.get(
                            f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}",
                            timeout=15.0
                        )
                        if response.status_code == 200:
                            data = response.json()
                            for m in data.get("models", []):
                                if "generateContent" in m.get("supportedGenerationMethods", []):
                                    models.append({
                                        "id": f"gemini/{m.get('name').replace('models/', '')}",
                                        "name": m.get('name').replace('models/', ''),
                                        "description": m.get('description', ''),
                                        "context_length": m.get("inputTokenLimit"),
                                        "pricing": {}
                                    })
                except Exception as e:
                    logger.debug(f"Error obteniendo modelos de Gemini API: {e}")
            
            if not models:
                models = [
                    {"id": "gemini/gemini-2.0-flash-exp", "name": "Gemini 2.0 Flash Exp"},
                    {"id": "gemini/gemini-2.0-flash", "name": "Gemini 2.0 Flash"},
                    {"id": "gemini/gemini-1.5-flash", "name": "Gemini 1.5 Flash"},
                    {"id": "gemini/gemini-1.5-pro", "name": "Gemini 1.5 Pro"},
                ]
            logger.info(f"Obtenidos {len(models)} modelos de Google/Gemini")

        elif provider == "deepseek":
            api_key = user_api_key
            if not api_key:
                api_key = os.getenv("DEEPSEEK_API_KEY")
            
            if api_key:
                api_base = user_api_base or "https://api.deepseek.com"
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.get(
                            f"{api_base}/models",
                            headers={"Authorization": f"Bearer {api_key}"},
                            timeout=15.0
                        )
                        if response.status_code == 200:
                            data = response.json()
                            for m in data.get("data", []):
                                models.append({
                                    "id": f"deepseek/{m.get('id')}",
                                    "name": m.get('id'),
                                    "context_length": m.get("context_length"),
                                })
                except Exception:
                    models = [
                        {"id": "deepseek/deepseek-chat", "name": "DeepSeek Chat"},
                        {"id": "deepseek/deepseek-reasoner", "name": "DeepSeek Reasoner"},
                    ]
            else:
                models = [
                    {"id": "deepseek/deepseek-chat", "name": "DeepSeek Chat"},
                ]
            logger.info(f"Obtenidos {len(models)} modelos de DeepSeek")

        elif provider == "mistral":
            api_key = user_api_key
            if not api_key:
                api_key = os.getenv("MISTRAL_API_KEY")
            
            if api_key:
                api_base = user_api_base or "https://api.mistral.ai"
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.get(
                            f"{api_base}/v1/models",
                            headers={"Authorization": f"Bearer {api_key}"},
                            timeout=15.0
                        )
                        if response.status_code == 200:
                            data = response.json()
                            for m in data.get("data", []):
                                models.append({
                                    "id": f"mistral/{m.get('id')}",
                                    "name": m.get('id'),
                                    "context_length": m.get("context_length"),
                                })
                except Exception:
                    models = [
                        {"id": "mistral/mistral-large-latest", "name": "Mistral Large"},
                        {"id": "mistral/mistral-small-latest", "name": "Mistral Small"},
                        {"id": "mistral/mistral-medium-latest", "name": "Mistral Medium"},
                    ]
            else:
                models = [
                    {"id": "mistral/mistral-large-latest", "name": "Mistral Large"},
                    {"id": "mistral/mistral-small-latest", "name": "Mistral Small"},
                ]
            logger.info(f"Obtenidos {len(models)} modelos de Mistral")

        elif provider == "groq":
            api_key = user_api_key
            if not api_key:
                api_key = os.getenv("GROQ_API_KEY")
            
            if api_key:
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.get(
                            "https://api.groq.com/openai/v1/models",
                            headers={"Authorization": f"Bearer {api_key}"},
                            timeout=15.0
                        )
                        if response.status_code == 200:
                            data = response.json()
                            for m in data.get("data", []):
                                models.append({
                                    "id": f"groq/{m.get('id')}",
                                    "name": m.get('id'),
                                    "context_length": m.get("context_length"),
                                })
                except Exception:
                    models = [
                        {"id": "groq/llama-3.3-70b-versatile", "name": "Llama 3.3 70B Versatile"},
                        {"id": "groq/llama-3.1-8b-instant", "name": "Llama 3.1 8B Instant"},
                        {"id": "groq/gemma-7b-it", "name": "Gemma 7B"},
                        {"id": "groq/mixtral-8x7b-32768", "name": "Mixtral 8x7B"},
                    ]
            else:
                models = [
                    {"id": "groq/llama-3.3-70b-versatile", "name": "Llama 3.3 70B Versatile"},
                    {"id": "groq/llama-3.1-8b-instant", "name": "Llama 3.1 8B Instant"},
                ]
            logger.info(f"Obtenidos {len(models)} modelos de Groq")

        elif provider == "cerebras":
            api_key = user_api_key
            if not api_key:
                api_key = os.getenv("CEREBRAS_API_KEY")
            
            if api_key:
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.get(
                            "https://api.cerebras.ai/v1/models",
                            headers={"Authorization": f"Bearer {api_key}"},
                            timeout=15.0
                        )
                        if response.status_code == 200:
                            data = response.json()
                            for m in data.get("data", []):
                                models.append({
                                    "id": f"cerebras/{m.get('id')}",
                                    "name": m.get('id'),
                                })
                except Exception:
                    models = [
                        {"id": "cerebras/llama-3.1-8b-instruct", "name": "Llama 3.1 8B Instruct"},
                        {"id": "cerebras/llama-3.3-70b-instruct", "name": "Llama 3.3 70B Instruct"},
                    ]
            else:
                models = [
                    {"id": "cerebras/llama-3.1-8b-instruct", "name": "Llama 3.1 8B Instruct"},
                ]
            logger.info(f"Obtenidos {len(models)} modelos de Cerebras")

        elif provider in ["ollama", "ollama-cloud"]:
            if provider == "ollama-cloud":
                # Para la nube, priorizamos el base del usuario o el default cloud
                # Ignoramos settings globales que suelen ser para el host local
                # Para la nube, priorizamos el base del usuario si no es un endpoint local evidente
                is_local = any(x in (user_api_base or "") for x in ["localhost", "127.0.0.1", "host.docker.internal", "8086", "11434"])
                ollama_base = user_api_base if (user_api_base and not is_local) else "https://ollama.com"
            else:
                # Para ollama local
                ollama_base = user_api_base or settings.llm_api_base or settings.ollama_api_url or "http://localhost:11434"
            
            logger.info(f"Intentando obtener modelos de Ollama ({provider}) en: {ollama_base}")
            try:
                headers = {}
                if provider == "ollama-cloud" and user_api_key:
                    headers["Authorization"] = f"Bearer {user_api_key}"
                
                async with httpx.AsyncClient() as client:
                    # Asegurar que no duplicamos /api/tags si ya viene en la base
                    url = f"{ollama_base.rstrip('/')}/api/tags"
                    response = await client.get(url, headers=headers, timeout=10.0)
                    if response.status_code == 200:
                        data = response.json()
                        raw_models = data.get("models", [])
                        for m in raw_models:
                            name = m.get("name")
                            models.append({
                                "id": f"ollama/{name}",
                                "name": name,
                                "size": m.get("size"),
                                "digest": m.get("digest"),
                            })
                        logger.info(f"Obtenidos {len(models)} modelos reales de Ollama en {ollama_base}")
                    else:
                        logger.warning(f"Ollama respondió con error {response.status_code} en {ollama_base}")
            except Exception as e:
                    logger.warning(f"Ollama no disponible o error en {ollama_base}: {str(e)}")
            
            if not models:
                logger.info(f"No se detectaron modelos en {ollama_base}, usando modelo de respaldo.")
                models = [{"id": "ollama/llama3", "name": f"Llama 3 (No detectado en {ollama_base})"}]
            
            return models

        elif provider == "openai-compatible":
            # Para cualquier servidor compatible con la API de OpenAI: Local AI, LM Studio, Ollama con API OpenAI, etc.
            if not user_api_base:
                return [{"id": "openai-compatible/sin-configurar", "name": "⚠️ Ingresa tu API Base URL primero"}]
            
            api_base = user_api_base.rstrip("/")
            # Intentar con /v1/models y también sin /v1 por si el usuario ya lo incluyó
            endpoints_to_try = []
            if "/v1" in api_base:
                endpoints_to_try = [f"{api_base}/models"]
            else:
                endpoints_to_try = [f"{api_base}/v1/models", f"{api_base}/models"]

            logger.info(f"Intentando obtener modelos de servidor OpenAI-compatible en: {api_base}")
            
            for endpoint in endpoints_to_try:
                try:
                    async with httpx.AsyncClient() as client:
                        headers = {}
                        if user_api_key:
                            headers["Authorization"] = f"Bearer {user_api_key}"
                        else:
                            headers["Authorization"] = "Bearer local-key"  # Local AI no requiere key real
                        
                        response = await client.get(endpoint, headers=headers, timeout=8.0)
                        if response.status_code == 200:
                            data = response.json()
                            raw_models = data.get("data", [])
                            for m in raw_models:
                                model_id = m.get("id", "")
                                models.append({
                                    "id": f"openai/{model_id}",
                                    "name": model_id,
                                })
                            logger.info(f"Obtenidos {len(models)} modelos de servidor local en {endpoint}")
                            break  # Salir del loop si tuvo éxito
                        else:
                            logger.warning(f"Endpoint {endpoint} respondió con {response.status_code}")
                except Exception as e:
                    logger.warning(f"Error al conectar con {endpoint}: {str(e)}")
                    continue
            
            if not models:
                return [{"id": "openai-compatible/error", "name": f"⚠️ No se pudo conectar a {api_base}"}]
            
            return models

        elif provider == "huggingface":
            api_key = user_api_key
            if not api_key:
                api_key = os.getenv("HF_TOKEN")
            
            models = [
                {"id": "huggingface/meta-llama/Meta-Llama-3-8B-Instruct", "name": "Llama 3 8B Instruct"},
                {"id": "huggingface/meta-llama/Meta-Llama-3-70B-Instruct", "name": "Llama 3 70B Instruct"},
                {"id": "huggingface/mistralai/Mistral-7B-Instruct-v0.1", "name": "Mistral 7B Instruct"},
            ]
            logger.info(f"Obtenidos {len(models)} modelos de Hugging Face")

        elif provider == "azure":
            api_key = user_api_key
            api_base = user_api_base
            
            if api_key and api_base:
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.get(
                            f"{api_base}/openai/models",
                            headers={"api-key": api_key},
                            timeout=15.0
                        )
                        if response.status_code == 200:
                            data = response.json()
                            for m in data.get("data", []):
                                models.append({
                                    "id": f"azure/{m.get('id')}",
                                    "name": m.get('id'),
                                })
                except Exception:
                    pass
            
            if not models:
                models = [
                    {"id": "azure/gpt-4o", "name": "GPT-4o (Azure)"},
                    {"id": "azure/gpt-4o-mini", "name": "GPT-4o Mini (Azure)"},
                    {"id": "azure/gpt-4-turbo", "name": "GPT-4 Turbo (Azure)"},
                    {"id": "azure/gpt-35-turbo", "name": "GPT-3.5 Turbo (Azure)"},
                ]
            logger.info(f"Obtenidos {len(models)} modelos de Azure")

        elif provider == "kilocode":
            # Kilocode Gateway - API unificada de IA
            api_key = (user_api_key or os.getenv("KILOCODE_API_KEY") or "").strip()
            if api_key and not api_key.isascii():
                logger.warning("KILOCODE_API_KEY contains non-ASCII characters. Stripping them.")
                api_key = api_key.encode('ascii', 'ignore').decode('ascii')
            # Kilocode usa una API base fija, no usa la del usuario
            kilocode_base = "https://api.kilo.ai/api/gateway"
            
            if api_key:
                # Intentar con /models y /v1/models por si acaso
                endpoints = [f"{kilocode_base}/v1/models", f"{kilocode_base}/models"]
                for endpoint in endpoints:
                    try:
                        async with httpx.AsyncClient() as client:
                            response = await client.get(
                                endpoint,
                                headers={"Authorization": f"Bearer {api_key}"},
                                timeout=15.0
                            )
                            if response.status_code == 200:
                                data = response.json()
                                raw_models = data.get("data", [])
                                if not raw_models and isinstance(data, list):
                                    raw_models = data
                                
                                for m in raw_models:
                                    model_id = m.get("id", "")
                                    model_name = m.get("name") or model_id
                                    models.append({
                                        "id": f"kilocode/{model_id}",
                                        "name": model_name,
                                        "context_length": m.get("context_length"),
                                        "pricing": m.get("pricing", {})
                                    })
                                logger.info(f"Obtenidos {len(models)} modelos de Kilocode Gateway desde {endpoint}")
                                break # Éxito, salir del loop de endpoints
                            else:
                                logger.warning(f"Kilocode ({endpoint}) respondió con error {response.status_code}")
                    except Exception as e:
                        logger.warning("Error al conectar con Kilocode Gateway (%s): %s", endpoint, str(e))
            
            if not models:
                # No devolvemos modelos por defecto para evitar el comportamiento hardcodeado
                models = []
                logger.info(f"No se pudieron obtener modelos de Kilocode Gateway, lista vacía.")

        else:
            logger.warning(f"Proveedor '{provider}' no reconocido.")
            models = []

        # Guardar en caché si obtuvimos resultados
        if models:
            _models_cache[provider] = {
                "timestamp": now,
                "models": models
            }
            
        return models

    except Exception as e:
        logger.error(f"Error al obtener modelos de {provider}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"No se pudieron obtener los modelos de {provider}")
