# utils/audio_transcriber.py

import logging
import asyncio
import functools
from typing import Optional
from io import BytesIO
from pydub import AudioSegment # Importar pydub
import os # Importar os para manejar archivos temporales

from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

WHISPER_MODEL_SIZE = "small"
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
    logger.critical("--- RUNNING NEW VERSION OF TRANSCRIBE AUDIO FILE ---")
    model = await get_whisper_model()
    if not model:
        logger.error("El modelo de transcripción no está disponible.")
        return None

    temp_file_path = None
    try:
        # Log para verificar el tamaño del audio antes de transcribir
        audio_file.seek(0, 2)
        file_size = audio_file.tell()
        audio_file.seek(0)
        logger.info(f"Transcribiendo archivo de audio con tamaño: {file_size} bytes y formato: {file_format}.")

        # Usar un archivo temporal para evitar problemas con pipes y formatos como webm
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_format}") as temp_file:
            temp_file.write(audio_file.read())
            temp_file_path = temp_file.name
        
        audio_file.seek(0) # Resetear el puntero del BytesIO por si se necesita en otro lado

        # Convertir el audio a formato WAV usando pydub desde el archivo temporal
        audio_segment = AudioSegment.from_file(temp_file_path, format=file_format)
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
    finally:
        # Asegurarse de que el archivo temporal se elimine
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)

import numpy as np

import collections

import subprocess

import tempfile # Necesario para NamedTemporaryFile si se decide usarlo para debugging o alternativas

from fastapi import WebSocket, WebSocketDisconnect



class StreamingTranscriber:

    """

    Gestiona la transcripción de audio en tiempo real utilizando un proceso ffmpeg persistente

    y un modelo de Whisper, ejecutando las tareas de forma asíncrona.

    """

    def __init__(self, model: WhisperModel, language: str = "es", chunk_length_s: int = 5):

        self.model = model

        self.language = language

        self.chunk_length_s = chunk_length_s

        self.sample_rate = 16000

        self.vad_parameters = dict(min_silence_duration_ms=500)

        self.pcm_buffer = bytearray()



    async def _feed_ffmpeg(self, websocket: WebSocket, ffmpeg_process: asyncio.subprocess.Process):

        """Lee audio del WebSocket y lo escribe en el stdin de ffmpeg."""

        while True:

            try:

                audio_chunk = await websocket.receive_bytes()

                if ffmpeg_process.stdin.is_closing():

                    break

                ffmpeg_process.stdin.write(audio_chunk)

                await ffmpeg_process.stdin.drain()

            except (WebSocketDisconnect, asyncio.CancelledError):

                logger.info("Se detiene la alimentación a ffmpeg por desconexión o cancelación.")

                break

            except Exception as e:

                logger.error(f"Error leyendo desde el websocket: {e}")

                break

        

        try:

            if not ffmpeg_process.stdin.is_closing():

                ffmpeg_process.stdin.close()

        except Exception as e:

            logger.warning(f"Error cerrando stdin de ffmpeg: {e}")



    async def _process_pcm_and_transcribe(self, websocket: WebSocket, ffmpeg_process: asyncio.subprocess.Process):

        """Lee audio PCM de ffmpeg, lo acumula y lo transcribe en trozos."""

        bytes_per_sample = 2  # 16-bit PCM

        chunk_size_bytes = self.chunk_length_s * self.sample_rate * bytes_per_sample



        while True:

            try:

                # Leer 1 segundo de audio PCM a la vez para mantener la responsividad

                pcm_chunk = await ffmpeg_process.stdout.read(self.sample_rate * bytes_per_sample)

                if not pcm_chunk:

                    break  # ffmpeg cerró su salida



                self.pcm_buffer.extend(pcm_chunk)



                if len(self.pcm_buffer) >= chunk_size_bytes:

                    buffer_to_process = self.pcm_buffer

                    self.pcm_buffer = bytearray()  # Limpiar para el siguiente trozo



                    audio_np = np.frombuffer(buffer_to_process, dtype=np.int16).astype(np.float32) / 32768.0



                    loop = asyncio.get_running_loop()

                    transcribe_func = functools.partial(

                        self.model.transcribe,

                        audio_np,

                        language=self.language,

                        vad_filter=True,

                        vad_parameters=self.vad_parameters

                    )

                    segments, _ = await loop.run_in_executor(None, transcribe_func)

                    

                    transcript = " ".join([s.text for s in segments]).strip()



                    if transcript:

                        await websocket.send_json({"type": "transcript_chunk", "text": transcript + " "})



            except (asyncio.CancelledError, WebSocketDisconnect):

                logger.info("Se detiene la transcripción por cancelación o desconexión.")

                break

            except Exception as e:

                logger.error(f"Error procesando audio PCM: {e}", exc_info=True)

                break



    async def start_transcription_session(self, websocket: WebSocket, input_format: str = "webm"):
        """Inicia y gestiona la sesión completa de transcripción."""
        command = [
            "ffmpeg", "-hide_banner", "-loglevel", "error",
            "-f", input_format, "-i", "pipe:0",
            "-f", "s16le", "-acodec", "pcm_s16le",
            "-ac", "1", "-ar", str(self.sample_rate),
            "pipe:1"
        ]

        ffmpeg_process = await asyncio.create_subprocess_exec(
            *command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        logger.info(f"Proceso ffmpeg iniciado con PID: {ffmpeg_process.pid}")

        feed_task = asyncio.create_task(self._feed_ffmpeg(websocket, ffmpeg_process))
        transcribe_task = asyncio.create_task(self._process_pcm_and_transcribe(websocket, ffmpeg_process))

        done, pending = await asyncio.wait(
            [feed_task, transcribe_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

        for task in pending:
            task.cancel()
        
        if ffmpeg_process.returncode is None:
            ffmpeg_process.terminate()
            await ffmpeg_process.wait()

        stderr = await ffmpeg_process.stderr.read()
        if stderr:
            logger.error(f"ffmpeg stderr: {stderr.decode(errors='ignore')}")
            
        logger.info("Sesión de transcripción finalizada.")
