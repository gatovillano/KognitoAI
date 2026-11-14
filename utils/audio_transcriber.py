# utils/audio_transcriber.py

import logging
import os # Importar os para manejar archivos temporales
import sys

def _load_cuda_libs():
    try:
        import ctypes
        for sp in sys.path:
            if 'site-packages' not in sp:
                continue
            cublas_path = os.path.join(sp, "nvidia", "cublas", "lib", "libcublas.so.12")
            cudnn_path = os.path.join(sp, "nvidia", "cudnn", "lib", "libcudnn.so.9")
            
            if os.path.exists(cublas_path):
                ctypes.CDLL(cublas_path, mode=ctypes.RTLD_GLOBAL)
            if os.path.exists(cudnn_path):
                ctypes.CDLL(cudnn_path, mode=ctypes.RTLD_GLOBAL)
    except Exception:
        pass

_load_cuda_libs()

import torch # Importar torch
import asyncio
import functools
from typing import Optional
from io import BytesIO
from pydub import AudioSegment # Importar pydub
from pydub.exceptions import CouldntDecodeError
import numpy as np

import shutil
import tempfile

import av
from faster_whisper import WhisperModel


def _patch_pyav_open() -> None:
    """Garantiza compatibilidad entre faster-whisper y PyAV moderno (av >= 14),
    donde el argumento obsoleto 'metadata_errors' fue eliminado de av.open().
    """
    orig_open = getattr(av, "open", None)
    if orig_open is None or getattr(orig_open, "_kognito_patched", False):
        return

    @functools.wraps(orig_open)
    def _compat_av_open(*args, **kwargs):
        try:
            return orig_open(*args, **kwargs)
        except TypeError as exc:
            if "metadata_errors" in kwargs and "metadata_errors" in str(exc):
                cleaned_kwargs = dict(kwargs)
                cleaned_kwargs.pop("metadata_errors", None)
                return orig_open(*args, **cleaned_kwargs)
            raise

    _compat_av_open._kognito_patched = True  # type: ignore[attr-defined]
    av.open = _compat_av_open


_patch_pyav_open()

logger = logging.getLogger(__name__)


def check_ffmpeg_available() -> None:
    """Verifica que ffmpeg y ffprobe estén disponibles en el PATH.

    pydub los invoca como subprocesos para decodificar el audio, así que sin
    ellos la transcripción falla con un FileNotFoundError poco descriptivo.
    """
    missing = [bin_name for bin_name in ("ffmpeg", "ffprobe") if shutil.which(bin_name) is None]
    if missing:
        logger.error(
            "Faltan binarios requeridos en el sistema: %s. Instálalos con: sudo apt install -y ffmpeg",
            ", ".join(missing),
        )
        raise AudioTranscriptionError(
            "El servidor no tiene ffmpeg instalado, no se puede procesar el audio."
        )

WHISPER_MODEL_SIZE = "small"
# Ya no se usan constantes globales para device y compute_type
# WHISPER_DEVICE = "cpu"
# WHISPER_COMPUTE_TYPE = "int8"
_whisper_model: Optional[WhisperModel] = None


class AudioTranscriptionError(Exception):
    """Base para errores controlados de transcripción."""


class InvalidAudioFileError(AudioTranscriptionError):
    """Se lanza cuando el archivo de audio recibido está vacío, corrupto o incompleto."""


def load_whisper_model(force_cpu=False):
    """Carga el modelo de transcripción de forma síncrona al inicio de la aplicación."""
    global _whisper_model
    if _whisper_model is not None and not force_cpu:
        return
        
    # Detección de GPU y configuración dinámica
    use_gpu = torch.cuda.is_available() and not force_cpu
    if use_gpu:
        device = "cuda"
        compute_type = "float16"
        logger.info("✅ GPU detectada. Cargando modelo Whisper en GPU (cuda) con compute_type float16.")
    else:
        device = "cpu"
        compute_type = "int8"
        if force_cpu:
            logger.warning("⚠️ Forzando carga del modelo Whisper en CPU con compute_type int8 debido a fallos previos con CUDA.")
        else:
            logger.warning("⚠️ No se detectó GPU. Cargando modelo Whisper en CPU con compute_type int8.")

    logger.info(f"Cargando modelo Faster Whisper: {WHISPER_MODEL_SIZE}...")
    try:
        model_instance = WhisperModel(WHISPER_MODEL_SIZE, device=device, compute_type=compute_type)
        
        # Si se cargó en GPU, realizar una prueba rápida de transcripción (dry-run)
        # para garantizar que CUDA y bibliotecas dinámicas como cuBLAS funcionen correctamente.
        if use_gpu:
            logger.info("Realizando prueba rápida de GPU (dry-run) para verificar CUDA/cuBLAS...")
            # 1 segundo de silencio a 16kHz
            dummy_audio = np.zeros(16000, dtype=np.float32)
            segments, _ = model_instance.transcribe(dummy_audio, language="es")
            # Forzar la ejecución del generador consumiéndolo por completo
            list(segments)
            logger.info("✅ Prueba de GPU exitosa. GPU y bibliotecas CUDA totalmente funcionales.")
            
        _whisper_model = model_instance
        logger.info("Modelo Faster Whisper cargado y listo.")
    except Exception as e:
        logger.error(f"Error cargando o probando el modelo Faster Whisper con device={device}: {e}", exc_info=True)
        if device == "cuda":
            logger.warning("Intentando fallback a CPU...")
            load_whisper_model(force_cpu=True)
        else:
            _whisper_model = None

async def get_whisper_model() -> Optional[WhisperModel]:
    """Devuelve el modelo de transcripción previamente cargado."""
    if _whisper_model is None:
        logger.warning("El modelo de Whisper no ha sido cargado. Intentando cargar ahora...")
        load_whisper_model()
    return _whisper_model

async def transcribe_audio_file(audio_file: BytesIO, file_format: str) -> str:
    """
    Transcribe un archivo de audio usando el modelo Whisper.

    Args:
        audio_file: Un objeto BytesIO que contiene los datos del audio.
        file_format: El formato del archivo de audio (ej. "webm", "ogg").

    Returns:
        El texto transcrito.
    """
    logger.critical("--- RUNNING NEW VERSION OF TRANSCRIBE AUDIO FILE ---")
    check_ffmpeg_available()
    model = await get_whisper_model()
    if not model:
        logger.error("El modelo de transcripción no está disponible.")
        raise AudioTranscriptionError("El modelo de transcripción no está disponible.")

    temp_audio_path = None
    try:
        # Log para verificar el tamaño del audio antes de transcribir
        audio_file.seek(0, 2)
        file_size = audio_file.tell()
        audio_file.seek(0)
        logger.info(f"Transcribiendo archivo de audio con tamaño: {file_size} bytes y formato: {file_format}.")

        if file_size == 0:
            raise InvalidAudioFileError("El archivo de audio está vacío.")

        # Crear un archivo temporal para procesar el audio.
        # Esto evita problemas con ffmpeg y pipes (seekback error) al leer desde memoria.
        with tempfile.NamedTemporaryFile(suffix=f".{file_format}", delete=False) as temp_file:
            temp_file.write(audio_file.getvalue())
            temp_audio_path = temp_file.name
        
        logger.info(f"Procesando audio desde archivo temporal: {temp_audio_path}")
        try:
            audio_segment = AudioSegment.from_file(temp_audio_path, format=file_format)
        except CouldntDecodeError as exc:
            logger.warning(
                "No se pudo decodificar el audio recibido. Tamaño=%s bytes, formato=%s.",
                file_size,
                file_format,
            )
            raise InvalidAudioFileError(
                "El archivo de audio no es válido o está incompleto. Intenta grabarlo de nuevo."
            ) from exc
        
        # Convertir a formato WAV en memoria, que es el formato esperado por Whisper.
        wav_file = BytesIO()
        audio_segment.export(wav_file, format="wav")
        wav_file.seek(0)
        logger.info(f"Audio convertido a WAV en memoria. Tamaño: {wav_file.getbuffer().nbytes} bytes.")

        # Transcribir el audio WAV con el modelo Whisper.
        segments, info = model.transcribe(
            wav_file,
            language="es",
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500)
        )
        transcribed_text = " ".join([segment.text for segment in segments]).strip()
        
        if not transcribed_text:
            logger.info("No se detectó habla en el audio.")
            return "No se detectó habla en el audio. Por favor, intenta de nuevo."
            
        logger.info(f"Audio transcrito. Idioma detectado: {info.language}")
        return transcribed_text

    except InvalidAudioFileError:
        raise
    except Exception as e:
        logger.error(f"Error durante la transcripción: {e}", exc_info=True)
        raise AudioTranscriptionError("Ocurrió un error al procesar el audio.") from e
    finally:
        # Limpiar el archivo temporal
        if temp_audio_path and os.path.exists(temp_audio_path):
            try:
                os.remove(temp_audio_path)
                logger.debug(f"Archivo temporal eliminado: {temp_audio_path}")
            except Exception as cleanup_error:
                logger.warning(f"No se pudo eliminar el archivo temporal {temp_audio_path}: {cleanup_error}")

import collections
import json
import subprocess
from fastapi import WebSocket, WebSocketDisconnect

class StreamingTranscriber:
    """
    Gestiona la transcripción de audio en tiempo real utilizando un proceso ffmpeg persistente
    y el modelo Faster Whisper local, ejecutando las tareas de forma asíncrona.
    """
    def __init__(self, model: WhisperModel, language: str = "es", chunk_length_s: float = 2.0):
        self.model = model
        self.language = language
        self.chunk_length_s = chunk_length_s
        self.sample_rate = 16000
        self.vad_parameters = dict(min_silence_duration_ms=400)
        self.pcm_buffer = bytearray()

    async def _feed_ffmpeg(self, websocket: WebSocket, ffmpeg_process: asyncio.subprocess.Process):
        """Lee audio del WebSocket (datos binarios o comandos de control) y alimenta el stdin de ffmpeg."""
        while True:
            try:
                message = await websocket.receive()
                
                # Tratar tramas binarias (audio)
                if "bytes" in message and message["bytes"]:
                    data = message["bytes"]
                    if ffmpeg_process.stdin.is_closing():
                        break
                    ffmpeg_process.stdin.write(data)
                    await ffmpeg_process.stdin.drain()

                # Tratar tramas de texto (ping/pong o comandos JSON)
                elif "text" in message and message["text"]:
                    text = message["text"].strip()
                    if text == "ping":
                        try:
                            await websocket.send_text("pong")
                        except Exception:
                            pass
                    elif text == "pong":
                        pass
                    else:
                        try:
                            ctrl = json.loads(text)
                            if ctrl.get("type") in ("stop", "end") or ctrl.get("action") in ("stop", "end"):
                                logger.info("StreamingTranscriber: Señal de detención recibida por WebSocket.")
                                break
                        except Exception:
                            pass

            except (WebSocketDisconnect, asyncio.CancelledError):
                logger.info("Se detiene la alimentación a ffmpeg por desconexión o cancelación.")
                break
            except Exception as e:
                logger.error(f"Error leyendo desde el websocket: {e}")
                break

        try:
            if ffmpeg_process.stdin and not ffmpeg_process.stdin.is_closing():
                ffmpeg_process.stdin.close()
                await ffmpeg_process.stdin.wait_closed()
        except Exception as e:
            logger.warning(f"Error cerrando stdin de ffmpeg: {e}")

    async def _process_pcm_and_transcribe(self, websocket: WebSocket, ffmpeg_process: asyncio.subprocess.Process):
        """Lee audio PCM de ffmpeg, lo acumula y lo transcribe en trozos en tiempo real."""
        bytes_per_sample = 2  # 16-bit PCM
        chunk_size_bytes = int(self.chunk_length_s * self.sample_rate * bytes_per_sample)
        read_step = int(self.sample_rate * bytes_per_sample * 0.5)  # Leer cada 0.5s para alta responsividad

        while True:
            try:
                pcm_chunk = await ffmpeg_process.stdout.read(read_step)
                if not pcm_chunk:
                    break  # ffmpeg terminó o cerró su salida

                self.pcm_buffer.extend(pcm_chunk)

                if len(self.pcm_buffer) >= chunk_size_bytes:
                    buffer_to_process = bytes(self.pcm_buffer)
                    self.pcm_buffer.clear()

                    audio_np = np.frombuffer(buffer_to_process, dtype=np.int16).astype(np.float32) / 32768.0

                    if np.abs(audio_np).max() > 0.01:
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

        # Procesar remanente si queda audio en el buffer (mínimo 0.35s = ~11200 bytes)
        min_residual_bytes = int(0.35 * self.sample_rate * bytes_per_sample)
        if len(self.pcm_buffer) >= min_residual_bytes:
            try:
                buffer_to_process = bytes(self.pcm_buffer)
                self.pcm_buffer.clear()
                audio_np = np.frombuffer(buffer_to_process, dtype=np.int16).astype(np.float32) / 32768.0
                if np.abs(audio_np).max() > 0.01:
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
            except Exception as e:
                logger.error(f"Error procesando remanente de audio: {e}")

        try:
            await websocket.send_json({"type": "final_transcript", "text": ""})
        except Exception:
            pass

    async def start_transcription_session(self, websocket: WebSocket, input_format: str = "webm"):
        """Inicia y gestiona la sesión completa de transcripción."""
        check_ffmpeg_available()
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
