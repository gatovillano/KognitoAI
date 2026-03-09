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
async def get_provider_models(provider: str, current_account_id: str = Depends(get_current_account_id)):
    """
    Obtiene la lista de modelos disponibles directamente desde el proveedor.
    """
    provider = provider.lower()
    now = time.time()
    
    # Verificar caché
    if provider in _models_cache:
        cache_entry = _models_cache[provider]
        if now - cache_entry["timestamp"] < CACHE_TTL:
            logger.info(f"Retornando modelos de {provider} desde caché.")
            return cache_entry["models"]

    models = []
    
    try:
        # Obtener API key del usuario para este proveedor
        user_api_key = await get_user_api_key(current_account_id, provider)
        user_api_base = await get_user_api_base(current_account_id)
        
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

        elif provider == "ollama":
            ollama_base = user_api_base or settings.llm_api_base or "http://localhost:11434"
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{ollama_base}/api/tags", 
                        timeout=5.0
                    )
                    if response.status_code == 200:
                        data = response.json()
                        for m in data.get("models", []):
                            name = m.get("name")
                            models.append({
                                "id": f"ollama/{name}",
                                "name": name,
                                "size": m.get("size"),
                                "digest": m.get("digest"),
                            })
            except Exception as e:
                logger.debug(f"Ollama no disponible en {ollama_base}: {e}")
            
            if not models:
                models = [{"id": "ollama/llama3", "name": "Llama 3 (Local - no detectado)"}]
            logger.info(f"Obtenidos {len(models)} modelos de Ollama")

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
