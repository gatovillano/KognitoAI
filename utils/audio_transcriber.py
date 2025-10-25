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

async def transcribe_audio_file(audio_file: BytesIO, file_format: str) -> Optional[str]:
    """
    Transcribe un archivo de audio usando el modelo Whisper.

    Args:
        audio_file: Un objeto BytesIO que contiene los datos del audio.
        file_format: El formato del archivo de audio (ej. "webm", "ogg").

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
        logger.info(f"Transcribiendo archivo de audio con tamaño: {file_size} bytes y formato: {file_format}.")

        # Convertir el audio a formato WAV usando pydub
        audio_segment = AudioSegment.from_file(audio_file, format=file_format)
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

import numpy as np
import collections

class StreamingTranscriber:
    def __init__(self, model: WhisperModel, language: str = "es", chunk_length_s: float = 1.0):
        self.model = model
        self.language = language
        self.chunk_length_s = chunk_length_s
        self.audio_buffer = collections.deque()
        self.buffer_duration = 0.0
        self.sample_rate = 16000 # Whisper models expect 16kHz audio
        self.vad_parameters = dict(min_silence_duration_ms=500)
        self.current_segments = []
        self.last_transcript_length = 0

    def _resample_audio(self, audio_data: np.ndarray, original_sample_rate: int) -> np.ndarray:
        """Resample audio to 16kHz if necessary."""
        if original_sample_rate == self.sample_rate:
            return audio_data
        
        # Using a simple resampling for now, a more robust solution might use librosa or torchaudio
        # For simplicity, we'll just log a warning if not 16kHz and hope for the best or raise an error
        logger.warning(f"Audio original sample rate {original_sample_rate} != {self.sample_rate}. Resampling might be needed.")
        # Placeholder for actual resampling logic if needed.
        # For now, we assume the client sends 16kHz or Whisper handles it.
        return audio_data

    async def process_audio_chunk(self, audio_chunk_bytes: bytes, file_format: str) -> Optional[str]:
        """
        Procesa un fragmento de audio, lo añade al buffer y devuelve una transcripción parcial si hay suficiente audio.
        """
        try:
            # Convertir el chunk a AudioSegment
            audio_segment = AudioSegment.from_file(BytesIO(audio_chunk_bytes), format=file_format)
            
            # Convertir a numpy array y resamplear si es necesario
            # Whisper espera audio en formato float32 y 16kHz
            audio_np = np.frombuffer(audio_segment.raw_data, dtype=np.int16).astype(np.float32) / 32768.0
            audio_np = self._resample_audio(audio_np, audio_segment.frame_rate)

            self.audio_buffer.append(audio_np)
            self.buffer_duration += audio_segment.duration_seconds

            current_transcript = ""
            
            # Si tenemos suficiente audio en el buffer, intentar transcribir
            if self.buffer_duration >= self.chunk_length_s:
                # Concatenar el buffer
                full_audio = np.concatenate(list(self.audio_buffer))
                
                # Transcribir el audio acumulado
                segments, info = self.model.transcribe(
                    full_audio,
                    language=self.language,
                    vad_filter=True,
                    vad_parameters=self.vad_parameters
                )
                
                new_segments = [s.text for s in segments]
                
                # Comparar con la última transcripción para encontrar lo nuevo
                current_transcript = " ".join(new_segments).strip()
                
                if len(current_transcript) > self.last_transcript_length:
                    new_text = current_transcript[self.last_transcript_length:].strip()
                    self.last_transcript_length = len(current_transcript)
                    return new_text
                
                # Limpiar el buffer si ya se ha procesado
                self.audio_buffer.clear()
                self.buffer_duration = 0.0

            return None

        except Exception as e:
            logger.error(f"Error procesando chunk de audio en streaming: {e}", exc_info=True)
            return None

    async def finalize_transcription(self) -> Optional[str]:
        """
        Procesa cualquier audio restante en el buffer y devuelve la transcripción final.
        """
        if not self.audio_buffer:
            return None

        try:
            full_audio = np.concatenate(list(self.audio_buffer))
            segments, info = self.model.transcribe(
                full_audio,
                language=self.language,
                vad_filter=True,
                vad_parameters=self.vad_parameters
            )
            final_text = " ".join([s.text for s in segments]).strip()
            self.audio_buffer.clear()
            self.buffer_duration = 0.0
            self.last_transcript_length = 0
            return final_text
        except Exception as e:
            logger.error(f"Error finalizando transcripción en streaming: {e}", exc_info=True)
            return None