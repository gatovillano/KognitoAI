"""
Extractor SLM Embebido para Grafo de Conocimiento.
Carga y ejecuta el modelo local Qwen2.5-3B-Instruct GGUF directamente
dentro del proceso de Python usando llama-cpp-python sin depender de servidores externos.
"""

import logging
import json
import asyncio
import os
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

_slm_instance = None
_slm_lock = asyncio.Lock()


class EmbeddedSLMExtractor:
    """
    Gestor del SLM local embebido (Qwen2.5-3B-Instruct GGUF) usando llama-cpp-python.
    """

    def __init__(self, model_repo: str = "Qwen/Qwen2.5-3B-Instruct-GGUF", filename: str = "qwen2.5-3b-instruct-q4_k_m.gguf"):
        self.model_repo = model_repo
        self.filename = filename
        self.llm = None
        self.initialized = False
        self.fallback_mode = False

    async def initialize(self):
        """
        Descarga (vía huggingface_hub) y carga el modelo GGUF usando llama-cpp-python.
        """
        if self.initialized:
            return

        async with _slm_lock:
            if self.initialized:
                return

            try:
                # 1. Intentar descargar / localizar el modelo GGUF con huggingface_hub
                from huggingface_hub import hf_hub_download
                logger.info(f"📥 Verificando / Descargando modelo SLM local ({self.model_repo}/{self.filename})...")
                
                model_path = await asyncio.to_thread(
                    hf_hub_download,
                    repo_id=self.model_repo,
                    filename=self.filename
                )
                logger.info(f"✅ Modelo GGUF localizado en: {model_path}")

                # 2. Intentar cargar con llama-cpp-python
                try:
                    from llama_cpp import Llama
                    logger.info("⚡ Cargando modelo SLM Qwen2.5-3B en GPU/RAM vía llama-cpp-python...")
                    
                    def _load():
                        return Llama(
                            model_path=model_path,
                            n_gpu_layers=-1,  # Intentar meter todas las capas en VRAM (4GB alcanzable para 3B Q4)
                            n_ctx=4096,       # Ventana de contexto amplia
                            verbose=False
                        )

                    self.llm = await asyncio.to_thread(_load)
                    logger.info("✅ SLM Qwen2.5-3B cargado exitosamente en el proceso embebido.")
                except ImportError:
                    logger.warning("⚠️ 'llama-cpp-python' no está instalado. Se usará el modo fallback con LLM Rápido.")
                    self.fallback_mode = True
                except Exception as e:
                    logger.warning(f"⚠️ No se pudo inicializar llama-cpp-python con GPU: {e}. Intentando en modo fallback...")
                    self.fallback_mode = True

            except Exception as e:
                logger.error(f"❌ Error al preparar modelo SLM embebido: {e}")
                self.fallback_mode = True

            self.initialized = True

    async def extract(self, user_message: str, ai_message: str, workspace_name: str) -> Optional[Dict[str, Any]]:
        """
        Ejecuta la extracción de conocimiento usando el SLM local embebido.
        """
        await self.initialize()

        system_prompt = f"""Eres un extractor estricto de conocimiento estructurado para un grafo de conocimiento.
Tu objetivo es analizar la conversación del usuario y asistente en el workspace "{workspace_name}" y devolver únicamente conceptos clave y relaciones significativas.

REGLAS DE EXCLUSIÓN (MUY IMPORTANTE):
1. PROHIBIDO extraer palabras conversacionales o de interfaz como: "bot", "chat", "mensaje", "respuesta", "usuario", "heartbeat", "revisa", "intento", "pregunta", "hola", "gracias".
2. NO extraigas palabras genéricas como "sistema", "datos", "información" a menos que formen parte de un nombre técnico específico (ej. "Sistema de Autenticación JWT").
3. Solo extrae Entidades de Alto Valor (Tecnologías, Herramientas, Arquitecturas, Organizaciones, Personas, Funcionalidades Clave).

Responde ÚNICAMENTE con un objeto JSON válido con la siguiente estructura exacta:
{{
    "conceptual_insights": [
        {{
            "concept": "Nombre del concepto de alto nivel",
            "full_text": "Explicación o conclusión clave",
            "category": "teoría/estrategia/metodología/arquitectura",
            "importance": "alta/media"
        }}
    ],
    "entities": [
        {{
            "name": "Nombre exacto de la entidad",
            "type": "TECHNOLOGY/TOOL/ORGANIZATION/PERSON/FEATURE",
            "description": "Breve contexto de la entidad"
        }}
    ],
    "relationships": [
        {{
            "source": "Nombre origen exacto",
            "target": "Nombre destino exacto",
            "type": "USES/DEPENDS_ON/IMPLEMENTS/REFINES/PART_OF",
            "description": "Motivo de la conexión"
        }}
    ]
}}"""

        user_content = f"Usuario: {user_message[:1000]}\nAsistente: {ai_message[:1500]}"

        # Si estamos en fallback mode o el modelo no cargó, usamos get_fast_llm()
        if self.fallback_mode or not self.llm:
            try:
                from core.llm_manager import get_fast_llm
                from langchain_core.messages import SystemMessage, HumanMessage
                
                logger.info("ℹ️ Ejecutando extracción vía LLM Fallback (LangChain / LLM Rápido)...")
                fast_llm = get_fast_llm()
                resp = await fast_llm.ainvoke([
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_content)
                ])
                raw_text = str(resp.content).strip()
            except Exception as e:
                logger.error(f"❌ Error en fallback de extracción: {e}")
                return None
        else:
            try:
                logger.info("⚡ Ejecutando inferencia local sincrónica en llama-cpp...")
                
                def _infer():
                    response = self.llm.create_chat_completion(
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_content}
                        ],
                        temperature=0.1,
                        response_format={"type": "json_object"}
                    )
                    return response["choices"][0]["message"]["content"]

                raw_text = await asyncio.to_thread(_infer)
            except Exception as e:
                logger.error(f"❌ Error durante inferencia en llama-cpp-python: {e}")
                return None

        # Limpiar y parsear JSON
        try:
            cleaned_text = raw_text.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.startswith("```"):
                cleaned_text = cleaned_text[3:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]

            parsed = json.loads(cleaned_text.strip())
            return parsed
        except Exception as e:
            logger.warning(f"⚠️ Error al parsear JSON devuelto por SLM: {e}. Texto bruto: {raw_text[:200]}")
            return None


def get_embedded_slm_extractor() -> EmbeddedSLMExtractor:
    """Devuelve la instancia singleton del extractor SLM embebido."""
    global _slm_instance
    if _slm_instance is None:
        _slm_instance = EmbeddedSLMExtractor()
    return _slm_instance
