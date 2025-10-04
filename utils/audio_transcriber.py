# utils/audio_transcriber.py

import logging
import asyncio
from typing import Optional
from io import BytesIO
from pydub import AudioSegment # Importar pydub

from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

WHISPER_MODEL_SIZE = "medium"
WHISPER_DEVICE = "cpu"
WHISPER_COMPUTE_TYPE = "int8"
_whisper_model: Optional[WhisperModel] = None

def load_whisper_model():
    """Carga el modelo de transcripción de forma síncrona al inicio de la aplicación."""
    global _whisper_model
    if _whisper_model is None:
        logger.info(f"Cargando modelo Faster Whisper: {WHISPER_MODEL_SIZE}...")
        try:
            _whisper_model = WhisperModel(WHISPER_MODEL_SIZE, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE_TYPE)
            logger.info("Modelo Faster Whisper cargado y listo.")
        except Exception as e:
            logger.error(f"Error cargando el modelo Faster Whisper: {e}", exc_info=True)
            _whisper_model = None

async def get_whisper_model() -> Optional[WhisperModel]:
    """Devuelve el modelo de transcripción previamente cargado."""
    if _whisper_model is None:
        logger.warning("El modelo de Whisper no ha sido cargado. Intentando cargar ahora...")
        load_whisper_model()
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
        # Log para verificar el tamaño del audio antes de transcribir
        audio_file.seek(0, 2)
        file_size = audio_file.tell()
        audio_file.seek(0)
        logger.info(f"Transcribiendo archivo de audio con tamaño: {file_size} bytes.")

        # Convertir el audio a formato WAV usando pydub
        audio_segment = AudioSegment.from_file(audio_file, format="webm")
        wav_file = BytesIO()
        audio_segment.export(wav_file, format="wav")
        wav_file.seek(0)
        logger.info(f"Audio convertido a WAV. Tamaño: {wav_file.getbuffer().nbytes} bytes.")

        # Especificar el idioma a español para mejorar la precisión
        segments, info = model.transcribe(
            wav_file, # Pasar el archivo WAV convertido
            language="es",
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500) # Ajustar la duración mínima de silencio
        )
        transcribed_text = " ".join([segment.text for segment in segments]).strip()
        
        if not transcribed_text:
            logger.info("No se detectó habla en el audio.")
            return "No se detectó habla en el audio. Por favor, intenta de nuevo."
            
        logger.info(f"Audio transcrito. Idioma detectado: {info.language}")
        return transcribed_text
    except Exception as e:
        logger.error(f"Error durante la transcripción: {e}", exc_info=True)
        return None
