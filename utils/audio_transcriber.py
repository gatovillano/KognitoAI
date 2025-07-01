# utils/audio_transcriber.py

import logging
import asyncio
from typing import Optional
from io import BytesIO

from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

WHISPER_MODEL_SIZE = "small"
WHISPER_DEVICE = "cpu"
WHISPER_COMPUTE_TYPE = "int8"
_whisper_model: Optional[WhisperModel] = None

async def get_whisper_model() -> Optional[WhisperModel]:
    """Carga y devuelve el modelo de transcripción, inicializándolo solo una vez."""
    global _whisper_model
    if _whisper_model is None:
        logger.info(f"Cargando modelo Faster Whisper: {WHISPER_MODEL_SIZE}...")
        try:
            loop = asyncio.get_event_loop()
            _whisper_model = await loop.run_in_executor(
                None,
                lambda: WhisperModel(WHISPER_MODEL_SIZE, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE_TYPE)
            )
            logger.info("Modelo Faster Whisper cargado.")
        except Exception as e:
            logger.error(f"Error cargando el modelo Faster Whisper: {e}", exc_info=True)
            _whisper_model = None
    return _whisper_model

async def transcribe_audio_file(audio_file: BytesIO) -> Optional[str]:
    """
    Transcribe un archivo de audio usando el modelo Whisper.

    Args:
        audio_file: Un objeto BytesIO que contiene los datos del audio.

    Returns:
        El texto transcrito, o None si ocurre un error.
    """
    model = await get_whisper_model()
    if not model:
        logger.error("El modelo de transcripción no está disponible.")
        return None

    try:
        segments, info = model.transcribe(audio_file)
        transcribed_text = " ".join([segment.text for segment in segments])
        logger.info(f"Audio transcrito. Idioma detectado: {info.language}")
        return transcribed_text
    except Exception as e:
        logger.error(f"Error durante la transcripción: {e}", exc_info=True)
        return None
