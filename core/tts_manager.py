import logging
import os
import hashlib
import json
from typing import Optional, List, AsyncGenerator, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path
from abc import ABC, abstractmethod
import asyncio
import uuid # Añadido para UUIDs
from openai import AsyncOpenAI # Añadido para OpenAI TTS

# Para Azure TTS
import azure.cognitiveservices.speech as speechsdk # Añadido para Azure TTS

# Para la configuración y secretos
from core.config import settings # Añadido para settings
from core.repositories.secret_repository import SecretRepository # Añadido para SecretRepository
from core.database import SessionLocal # Necesario para obtener la configuración del usuario

from google.cloud import texttospeech
from google.oauth2 import service_account
from google.api_core.exceptions import GoogleAPICallError, RetryError

logger = logging.getLogger(__name__)

# --- TTS Cache (reutilizado de google_tts.py) ---
class TTSCache:
    """
    Sistema de caché para audios generados por TTS.
    
    Almacena los audios en disco y mantiene un índice en memoria
    para acceso rápido. Los audios se identifican por un hash
    del texto, voz y configuración.
    """
    
    def __init__(self, cache_dir: Optional[str] = None, max_age_days: int = 30):
        """
        Inicializa el caché de TTS.
        
        Args:
            cache_dir: Directorio para almacenar los archivos de audio
            max_age_days: Días máximos para mantener un audio en caché
        """
        self.cache_dir = Path(cache_dir) if cache_dir else Path("/tmp/tts_cache")
        self.max_age_days = max_age_days
        self.memory_cache: Dict[str, Dict[str, Any]] = {}
        
        # Crear directorio si no existe
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Cargar índice existente
        self._load_index()
        
        logger.info(f"✅ Caché de TTS inicializado en: {self.cache_dir}")
    
    def _get_cache_key(self, text: str, voice: str, speaking_rate: float, audio_format: str) -> str:
        """
        Genera una clave única para el caché basada en los parámetros.
        
        Args:
            text: Texto a convertir
            voice: Voz utilizada
            speaking_rate: Velocidad de habla
            audio_format: Formato de audio
            
        Returns:
            Hash MD5 de los parámetros
        """
        key_data = f"{text}:{voice}:{speaking_rate}:{audio_format}"
        return hashlib.md5(key_data.encode('utf-8')).hexdigest()
    
    def _get_index_path(self) -> Path:
        """Obtiene la ruta del archivo de índice."""
        return self.cache_dir / "cache_index.json"
    
    def _load_index(self):
        """Carga el índice de caché desde disco."""
        index_path = self._get_index_path()
        if index_path.exists():
            try:
                with open(index_path, 'r', encoding='utf-8') as f:
                    self.memory_cache = json.load(f)
                logger.info(f"📂 Índice de caché cargado: {len(self.memory_cache)} entradas")
            except Exception as e:
                logger.warning(f"⚠️ Error cargando índice de caché: {e}")
                self.memory_cache = {}
    
    def _save_index(self):
        """Guarda el índice de caché en disco."""
        try:
            with open(self._get_index_path(), 'w', encoding='utf-8') as f:
                json.dump(self.memory_cache, f, indent=2)
        except Exception as e:
            logger.warning(f"⚠️ Error guardando índice de caché: {e}")
    
    def _is_expired(self, timestamp: str) -> bool:
        """Verifica si una entrada del caché ha expirado."""
        try:
            cached_date = datetime.fromisoformat(timestamp)
            return datetime.now() - cached_date > timedelta(days=self.max_age_days)
        except:
            return True
    
    def get(self, text: str, voice: str, speaking_rate: float, audio_format: str) -> Optional[bytes]:
        """
        Obtiene un audio del caché si existe y no ha expirado.
        
        Args:
            text: Texto del audio
            voice: Voz utilizada
            speaking_rate: Velocidad de habla
            audio_format: Formato de audio
            
        Returns:
            Bytes del audio o None si no está en caché
        """
        cache_key = self._get_cache_key(text, voice, speaking_rate, audio_format)
        
        if cache_key not in self.memory_cache:
            return None
        
        entry = self.memory_cache[cache_key]
        
        # Verificar expiración
        if self._is_expired(entry.get('timestamp', '')):
            logger.debug(f"🗑️ Entrada de caché expirada: {cache_key[:8]}...")
            self._remove_entry(cache_key)
            return None
        
        # Verificar que el archivo existe
        file_path = Path(entry.get('file_path', ''))
        if not file_path.exists():
            logger.debug(f"🗑️ Archivo de caché no encontrado: {file_path}")
            self._remove_entry(cache_key)
            return None
        
        try:
            with open(file_path, 'rb') as f:
                audio_data = f.read()
            logger.debug(f"✅ Audio recuperado de caché: {cache_key[:8]}... ({len(audio_data)} bytes)")
            return audio_data
        except Exception as e:
            logger.warning(f"⚠️ Error leyendo archivo de caché: {e}")
            self._remove_entry(cache_key)
            return None
    
    def set(self, text: str, voice: str, speaking_rate: float, audio_format: str, audio_data: bytes):
        """
        Guarda un audio en el caché.
        
        Args:
            text: Texto del audio
            voice: Voz utilizada
            speaking_rate: Velocidad de habla
            audio_format: Formato de audio
            audio_data: Bytes del audio
        """
        cache_key = self._get_cache_key(text, voice, speaking_rate, audio_format)
        file_path = self.cache_dir / f"{cache_key}.{audio_format}"
        
        try:
            # Guardar archivo
            with open(file_path, 'wb') as f:
                f.write(audio_data)
            
            # Actualizar índice
            self.memory_cache[cache_key] = {
                'file_path': str(file_path),
                'timestamp': datetime.now().isoformat(),
                'text_preview': text[:100] + '...' if len(text) > 100 else text,
                'voice': voice,
                'size_bytes': len(audio_data)
            }
            
            self._save_index()
            logger.debug(f"💾 Audio guardado en caché: {cache_key[:8]}... ({len(audio_data)} bytes)")
            
        except Exception as e:
            logger.warning(f"⚠️ Error guardando en caché: {e}")
    
    def _remove_entry(self, cache_key: str):
        """Elimina una entrada del caché."""
        if cache_key in self.memory_cache:
            entry = self.memory_cache[cache_key]
            file_path = Path(entry.get('file_path', ''))
            
            # Eliminar archivo si existe
            try:
                if file_path.exists():
                    file_path.unlink()
            except Exception:
                pass
            
            # Eliminar del índice
            del self.memory_cache[cache_key]
            self._save_index()
    
    def clear_expired(self):
        """Limpia las entradas expiradas del caché."""
        expired_keys = [
            key for key, entry in self.memory_cache.items()
            if self._is_expired(entry.get('timestamp', ''))
        ]
        
        for key in expired_keys:
            self._remove_entry(key)
        
        if expired_keys:
            logger.info(f"🧹 {len(expired_keys)} entradas expiradas eliminadas del caché")
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del caché."""
        total_size = sum(
            entry.get('size_bytes', 0)
            for entry in self.memory_cache.values()
        )
        
        return {
            'total_entries': len(self.memory_cache),
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'cache_dir': str(self.cache_dir),
            'max_age_days': self.max_age_days
        }

# --- Interfaz Abstracta TTSService ---
class TTSService(ABC):
    """
    Interfaz abstracta para servicios de Text-to-Speech.
    Define los métodos que cualquier implementación de TTS debe proporcionar.
    """
    
    @abstractmethod
    async def synthesize_speech(
        self,
        text: str,
        voice: Optional[str] = None,
        speaking_rate: float = 1.0,
        pitch: float = 0.0,
        volume_gain_db: float = 0.0,
        audio_format: str = "mp3",
        use_cache: bool = True
    ) -> bytes:
        """
        Convierte texto a audio.
        
        Args:
            text: Texto a convertir a voz
            voice: Código de voz a utilizar
            speaking_rate: Velocidad de habla
            pitch: Tono de voz
            volume_gain_db: Ganancia de volumen en dB
            audio_format: Formato de audio
            use_cache: Si se debe usar el caché
            
        Returns:
            Bytes del audio generado
        """
        pass
    
    @abstractmethod
    async def synthesize_speech_streaming(
        self,
        text_chunks: List[str],
        voice: Optional[str] = None,
        speaking_rate: float = 1.0,
        audio_format: str = "mp3",
        use_cache: bool = True
    ) -> AsyncGenerator[bytes, None]:
        """
        Genera audio en streaming para múltiples fragmentos de texto.
        
        Args:
            text_chunks: Lista de fragmentos de texto a convertir
            voice: Código de voz a utilizar
            speaking_rate: Velocidad de habla
            audio_format: Formato de audio
            use_cache: Si se debe usar el caché
            
        Yields:
            Bytes de audio para cada fragmento
        """
        pass
    
    @abstractmethod
    def get_cache_stats(self) -> Optional[Dict[str, Any]]:
        """Obtiene estadísticas del caché si está habilitado."""
        pass
    
    @abstractmethod
    def clear_cache(self):
        """Limpia el caché de audios."""
        pass

# --- Implementación de GoogleTTSService ---
class GoogleTTSService(TTSService):
    """
    Implementación de TTSService para Google Cloud Text-to-Speech.
    """
    
    # Mapeo de códigos de voz simplificados a nombres completos de Google Cloud
    VOICE_MAP = {
        # Español (México)
        'es-MX-DaliaNeural': ('es-MX', 'es-MX-DaliaNeural'),
        'es-MX-JorgeNeural': ('es-MX', 'es-MX-JorgeNeural'),
        'es-MX-AndresNeural': ('es-MX', 'es-MX-AndresNeural'),
        'es-MX-FernandaNeural': ('es-MX', 'es-MX-FernandaNeural'),
        
        # Español (España)
        'es-ES-ElviraNeural': ('es-ES', 'es-ES-ElviraNeural'),
        'es-ES-AlvaroNeural': ('es-ES', 'es-ES-AlvaroNeural'),
        
        # Inglés (EE.UU.)
        'en-US-Neural2-A': ('en-US', 'en-US-Neural2-A'),
        'en-US-Neural2-C': ('en-US', 'en-US-Neural2-C'),
        'en-US-Neural2-D': ('en-US', 'en-US-Neural2-D'),
        'en-US-Neural2-E': ('en-US', 'en-US-Neural2-E'),
        'en-US-Neural2-F': ('en-US', 'en-US-Neural2-F'),
        'en-US-Neural2-G': ('en-US', 'en-US-Neural2-G'),
        'en-US-Neural2-H': ('en-US', 'en-US-Neural2-H'),
        'en-US-Neural2-I': ('en-US', 'en-US-Neural2-I'),
        'en-US-Neural2-J': ('en-US', 'en-US-Neural2-J'),
        
        # Inglés (Reino Unido)
        'en-GB-Neural2-A': ('en-GB', 'en-GB-Neural2-A'),
        'en-GB-Neural2-B': ('en-GB', 'en-GB-Neural2-B'),
        'en-GB-Neural2-C': ('en-GB', 'en-GB-Neural2-C'),
        'en-GB-Neural2-D': ('en-GB', 'en-GB-Neural2-D'),
        
        # Portugués (Brasil)
        'pt-BR-FranciscaNeural': ('pt-BR', 'pt-BR-FranciscaNeural'),
        'pt-BR-AntonioNeural': ('pt-BR', 'pt-BR-AntonioNeural'),
        
        # Francés (Francia)
        'fr-FR-JosephineNeural': ('fr-FR', 'fr-FR-JosephineNeural'),
        'fr-FR-DeniseNeural': ('fr-FR', 'fr-FR-DeniseNeural'),
        
        # Alemán (Alemania)
        'de-DE-KatjaNeural': ('de-DE', 'de-DE-KatjaNeural'),
        'de-DE-ConradNeural': ('de-DE', 'de-DE-ConradNeural'),
        
        # Italiano (Italia)
        'it-IT-ElsaNeural': ('it-IT', 'it-IT-ElsaNeural'),
        'it-IT-BiancaNeural': ('it-IT', 'it-IT-BiancaNeural'),
        
        # Japonés (Japón)
        'ja-JP-NanamiNeural': ('ja-JP', 'ja-JP-NanamiNeural'),
        'ja-JP-KeitaNeural': ('ja-JP', 'ja-JP-KeitaNeural'),
    }
    
    # Voz por defecto
    DEFAULT_VOICE = 'es-MX-DaliaNeural'
    
    def __init__(self, cache_enabled: bool = True, cache_dir: Optional[str] = None, api_key: Optional[str] = None):
        """
        Inicializa el cliente de Google Cloud Text-to-Speech.
        
        Args:
            cache_enabled: Si se debe habilitar el caché de audios
            cache_dir: Directorio para el caché (None para usar default)
            
        Requiere que la variable de entorno GOOGLE_APPLICATION_CREDENTIALS
        esté configurada con la ruta al archivo de credenciales de servicio,
        o que las credenciales se proporcionen explícitamente.
        """
        try:
            # Intentar cargar credenciales explícitamente
            credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            
            # Si no está en el entorno, buscar en la carpeta de credenciales conocida
            if not credentials_path:
                project_root = Path(__file__).parent.parent
                possible_paths = [
                    project_root / "credentials/gen-lang-client-0283065579-d517663d377f.json",
                    project_root / "credentials/gen-lang-client-0283065579-148403406341.json"
                ]
                for p in possible_paths:
                    if p.exists():
                        credentials_path = str(p)
                        # No seteamos os.environ para evitar colisiones, usamos explícitamente
                        logger.info(f"📍 Credenciales encontradas automáticamente en: {credentials_path}")
                        break

            if credentials_path and os.path.exists(credentials_path):
                credentials = service_account.Credentials.from_service_account_file(credentials_path)
                self.client = texttospeech.TextToSpeechClient(credentials=credentials)
                logger.info(f"✅ Cliente de Google Cloud TTS inicializado con credenciales de: {credentials_path}")
            else:
                # Fallback a credenciales por defecto (ADC)
                self.client = texttospeech.TextToSpeechClient()
                logger.info("✅ Cliente de Google Cloud TTS inicializado con Application Default Credentials")
                
        except Exception as e:
            logger.error(f"❌ Error al inicializar el cliente de Google Cloud TTS: {e}")
            # Si falla, intentar usar API Key si existe (algunas APIs de Google lo permiten como fallback)
            # Prioridad: 1. API Key pasada explícitamente, 2. Variable de entorno GOOGLE_API_KEY
            api_key = api_key or os.getenv("GOOGLE_API_KEY")
            if api_key:
                try:
                    self.client = texttospeech.TextToSpeechClient(client_options={"api_key": api_key})
                    logger.info("✅ Cliente de Google Cloud TTS inicializado usando GOOGLE_API_KEY")
                except Exception as inner_e:
                    logger.error(f"❌ También falló el intento con API Key: {inner_e}")
                    raise e
            else:
                raise e

        
        # Inicializar caché si está habilitado
        self.cache: Optional[TTSCache] = None
        if cache_enabled:
            self.cache = TTSCache(cache_dir=cache_dir)
    
    def _get_voice_config(self, voice_code: Optional[str] = None) -> tuple:
        """
        Obtiene la configuración de voz (language_code, voice_name) a partir del código.
        
        Args:
            voice_code: Código de voz (ej: 'es-MX-DaliaNeural')
            
        Returns:
            Tupla con (language_code, voice_name)
        """
        if not voice_code:
            voice_code = self.DEFAULT_VOICE
        
        # Buscar en el mapeo
        if voice_code in self.VOICE_MAP:
            return self.VOICE_MAP[voice_code]
        
        # Si no está en el mapeo, intentar inferir
        # Formato esperado: 'language-VoiceName'
        parts = voice_code.split('-')
        if len(parts) >= 3:
            # Reconstruir el código de idioma (ej: 'es-MX')
            lang_code = f"{parts[0]}-{parts[1]}"
            return (lang_code, voice_code)
        
        # Fallback a voz por defecto
        logger.warning(f"⚠️ Voz '{voice_code}' no reconocida, usando voz por defecto")
        return self.VOICE_MAP[self.DEFAULT_VOICE]
    
    async def synthesize_speech(
        self,
        text: str,
        voice: Optional[str] = None,
        speaking_rate: float = 1.0,
        pitch: float = 0.0,
        volume_gain_db: float = 0.0,
        audio_format: str = "mp3",
        use_cache: bool = True
    ) -> bytes:
        """
        Convierte texto a audio usando Google Cloud Text-to-Speech.
        
        Args:
            text: Texto a convertir a voz
            voice: Código de voz a utilizar (ej: 'es-MX-DaliaNeural')
            speaking_rate: Velocidad de habla (0.25 a 4.0, 1.0 = normal)
            pitch: Tono de voz (-20.0 a 20.0, 0.0 = normal)
            volume_gain_db: Ganancia de volumen en dB (-96.0 a 16.0)
            audio_format: Formato de audio ('mp3', 'ogg_opus', 'wav', 'linear16')
            use_cache: Si se debe usar el caché
            
        Returns:
            Bytes del audio generado
            
        Raises:
            GoogleAPICallError: Si hay un error en la llamada a la API
            RetryError: Si se agotan los reintentos
        """
        # Verificar caché primero
        if use_cache and self.cache and text:
            cached_audio = self.cache.get(text, voice or self.DEFAULT_VOICE, speaking_rate, audio_format)
            if cached_audio:
                logger.info(f"✅ Audio recuperado de caché ({len(cached_audio)} bytes)")
                return cached_audio
        
        try:
            # Obtener configuración de voz
            language_code, voice_name = self._get_voice_config(voice)
            
            # Configurar el texto de entrada
            input_text = texttospeech.SynthesisInput(text=text)
            
            # Configurar la voz
            voice_params = texttospeech.VoiceSelectionParams(
                language_code=language_code,
                name=voice_name
            )
            
            # Configurar el audio
            audio_encoding_map = {
                "mp3": texttospeech.AudioEncoding.MP3,
                "ogg_opus": texttospeech.AudioEncoding.OGG_OPUS,
                "wav": texttospeech.AudioEncoding.LINEAR16,  # WAV es LINEAR16
                "linear16": texttospeech.AudioEncoding.LINEAR16,
            }
            
            audio_encoding = audio_encoding_map.get(audio_format, texttospeech.AudioEncoding.MP3)
            
            audio_config = texttospeech.AudioConfig(
                audio_encoding=audio_encoding,
                speaking_rate=speaking_rate,
                pitch=pitch,
                volume_gain_db=volume_gain_db
            )
            
            # Realizar la síntesis (ejecutar en thread para no bloquear)
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.synthesize_speech(
                    input=input_text,
                    voice=voice_params,
                    audio_config=audio_config
                )
            )
            
            audio_content = response.audio_content
            
            # Guardar en caché
            if use_cache and self.cache and text:
                self.cache.set(text, voice or self.DEFAULT_VOICE, speaking_rate, audio_format, audio_content)
            
            logger.info(f"✅ Audio generado exitosamente: {len(audio_content)} bytes")
            return audio_content
            
        except GoogleAPICallError as e:
            logger.error(f"❌ Error de Google Cloud TTS: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Error inesperado en síntesis de voz: {e}")
            raise
    
    async def synthesize_speech_streaming(
        self,
        text_chunks: List[str],
        voice: Optional[str] = None,
        speaking_rate: float = 1.0,
        audio_format: str = "mp3",
        use_cache: bool = True
    ) -> AsyncGenerator[bytes, None]:
        """
        Genera audio en streaming para múltiples fragmentos de texto.
        
        Args:
            text_chunks: Lista de fragmentos de texto a convertir
            voice: Código de voz a utilizar
            speaking_rate: Velocidad de habla
            audio_format: Formato de audio
            use_cache: Si se debe usar el caché
            
        Yields:
            Bytes de audio para cada fragmento
        """
        for i, chunk in enumerate(text_chunks):
            if not chunk or not chunk.strip():
                continue
                
            try:
                audio_content = await self.synthesize_speech(
                    text=chunk,
                    voice=voice,
                    speaking_rate=speaking_rate,
                    audio_format=audio_format,
                    use_cache=use_cache
                )
                yield audio_content
                logger.debug(f"✅ Fragmento {i+1}/{len(text_chunks)} procesado")
            except Exception as e:
                logger.error(f"❌ Error procesando fragmento {i+1}: {e}")
                # Continuar con el siguiente fragmento
                continue
    
    def get_cache_stats(self) -> Optional[Dict[str, Any]]:
        """Obtiene estadísticas del caché si está habilitado."""
        if self.cache:
            return self.cache.get_stats()
        return None
    
    def clear_cache(self):
        """Limpia el caché de audios."""
        if self.cache:
            self.cache.clear_expired()

# --- Implementación de AzureTTSService ---
class AzureTTSService(TTSService):
    """
    Implementación de TTSService para Azure Cognitive Services Speech.
    """
    DEFAULT_VOICE = "es-MX-DaliaNeural" # Voz por defecto para Azure
    
    def __init__(self, cache_enabled: bool = True, cache_dir: Optional[str] = None, api_key: Optional[str] = None, region: Optional[str] = None):
        if not api_key:
            raise ValueError("API Key de Azure es requerida para AzureTTSService.")
        if not region:
            raise ValueError("Región de Azure es requerida para AzureTTSService.")
            
        self.speech_config = speechsdk.SpeechConfig(subscription=api_key, region=region)
        # Configurar el formato de salida de audio
        self.speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3)
        
        self.cache: Optional[TTSCache] = None
        if cache_enabled:
            self.cache = TTSCache(cache_dir=cache_dir)
        
        logger.info(f"✅ Cliente de Azure TTS inicializado para región '{region}'.")

    async def synthesize_speech(
        self,
        text: str,
        voice: Optional[str] = None,
        speaking_rate: float = 1.0,
        pitch: float = 0.0, # Azure no soporta pitch directamente en SpeechSynthesizer, se haría con SSML
        volume_gain_db: float = 0.0, # Azure no soporta volume_gain_db directamente, se haría con SSML
        audio_format: str = "mp3", # El formato ya está configurado en SpeechConfig
        use_cache: bool = True
    ) -> bytes:
        
        # Verificar caché primero
        if use_cache and self.cache and text:
            cached_audio = self.cache.get(text, voice or self.DEFAULT_VOICE, speaking_rate, audio_format)
            if cached_audio:
                logger.info(f"✅ Audio recuperado de caché ({len(cached_audio)} bytes)")
                return cached_audio

        # Crear un sintetizador de voz
        audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True) # No se usa para obtener bytes
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=self.speech_config, audio_config=None) # audio_config=None para obtener el resultado en memoria

        # Configurar la voz y la velocidad
        ssml_text = f"""
        <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="http://www.microsoft.com/mstts" xml:lang="en-US">
            <voice name="{voice or self.DEFAULT_VOICE}">
                <prosody rate="{speaking_rate:.2f}">
                    {text}
                </prosody>
            </voice>
        </speak>
        """
        
        result = await asyncio.to_thread(lambda: synthesizer.speak_ssml_async(ssml_text).get())
        
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            audio_content = result.audio_data
            # Guardar en caché
            if use_cache and self.cache and text:
                self.cache.set(text, voice or self.DEFAULT_VOICE, speaking_rate, audio_format, audio_content)
            logger.info(f"✅ Audio generado exitosamente con Azure TTS: {len(audio_content)} bytes")
            return audio_content
        elif result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = result.cancellation_details
            error_message = f"Síntesis de voz de Azure cancelada: {cancellation_details.reason}"
            if cancellation_details.reason == speechsdk.CancellationReason.Error:
                error_message += f". Código de error: {cancellation_details.error_details}"
            logger.error(f"❌ {error_message}")
            raise Exception(error_message)
        else:
            error_message = f"Error desconocido en la síntesis de voz de Azure: {result.reason}"
            logger.error(f"❌ {error_message}")
            raise Exception(error_message)

    async def synthesize_speech_streaming(
        self,
        text_chunks: List[str],
        voice: Optional[str] = None,
        speaking_rate: float = 1.0,
        audio_format: str = "mp3",
        use_cache: bool = True
    ) -> AsyncGenerator[bytes, None]:
        for i, chunk in enumerate(text_chunks):
            if not chunk or not chunk.strip():
                continue
            try:
                audio_content = await self.synthesize_speech(
                    text=chunk,
                    voice=voice,
                    speaking_rate=speaking_rate,
                    audio_format=audio_format,
                    use_cache=use_cache
                )
                yield audio_content
                logger.debug(f"✅ Fragmento {i+1}/{len(text_chunks)} procesado por Azure TTS")
            except Exception as e:
                logger.error(f"❌ Error procesando fragmento {i+1} con Azure TTS: {e}")
                continue
    
    def get_cache_stats(self) -> Optional[Dict[str, Any]]:
        if self.cache:
            return self.cache.get_stats()
        return None
    
    def clear_cache(self):
        if self.cache:
            self.cache.clear_expired()

# --- Implementación de OpenAITTSService ---
class OpenAITTSService(TTSService):
    """
    Implementación de TTSService para OpenAI y compatibles (ej. Kokoro local).
    """
    DEFAULT_VOICE = "alloy"
    
    def __init__(self, cache_enabled: bool = True, cache_dir: Optional[str] = None, api_key: Optional[str] = None, api_base: Optional[str] = None, model: Optional[str] = None):
        self.api_base = api_base or "https://api.openai.com/v1"
        self.api_key = api_key or "sk-dummy"
        self.model = model or "tts-1"
        
        # Traducir localhost a host.docker.internal si estamos en Docker
        if ("localhost" in self.api_base or "127.0.0.1" in self.api_base) and os.path.exists("/.dockerenv"):
            self.api_base = self.api_base.replace("localhost", "host.docker.internal").replace("127.0.0.1", "host.docker.internal")
            logger.info(f"🔄 Traduciendo local openai-compatible base a host.docker.internal: {self.api_base}")

        self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.api_base)
        
        self.cache: Optional[TTSCache] = None
        if cache_enabled:
            self.cache = TTSCache(cache_dir=cache_dir)
            
        logger.info(f"✅ Cliente de OpenAI TTS inicializado con base_url '{self.api_base}' y modelo '{self.model}'.")

    async def synthesize_speech(
        self,
        text: str,
        voice: Optional[str] = None,
        speaking_rate: float = 1.0,
        pitch: float = 0.0,
        volume_gain_db: float = 0.0,
        audio_format: str = "mp3",
        use_cache: bool = True
    ) -> bytes:
        
        # Verificar caché primero
        if use_cache and self.cache and text:
            cached_audio = self.cache.get(text, voice or self.DEFAULT_VOICE, speaking_rate, audio_format)
            if cached_audio:
                logger.info(f"✅ Audio recuperado de caché ({len(cached_audio)} bytes)")
                return cached_audio

        try:
            # Check type of response format, openai expects strings like "mp3", "opus", "aac", "flac"
            valid_formats = ["mp3", "opus", "aac", "flac", "wav", "pcm"]
            fmt = audio_format if audio_format in valid_formats else "mp3"

            response = await self.client.audio.speech.create(
                model=self.model,
                voice=voice or self.DEFAULT_VOICE,
                input=text,
                response_format=fmt,
                speed=speaking_rate
            )
            audio_content = response.content
            
            # Guardar en caché
            if use_cache and self.cache and text:
                self.cache.set(text, voice or self.DEFAULT_VOICE, speaking_rate, audio_format, audio_content)
                
            logger.info(f"✅ Audio generado exitosamente con OpenAI TTS: {len(audio_content)} bytes")
            return audio_content
        except Exception as e:
            logger.error(f"❌ Error en síntesis de voz de OpenAI: {e}")
            raise Exception(f"Error en OpenAI TTS: {e}")

    async def synthesize_speech_streaming(
        self,
        text_chunks: List[str],
        voice: Optional[str] = None,
        speaking_rate: float = 1.0,
        audio_format: str = "mp3",
        use_cache: bool = True
    ) -> AsyncGenerator[bytes, None]:
        for i, chunk in enumerate(text_chunks):
            if not chunk or not chunk.strip():
                continue
            try:
                audio_content = await self.synthesize_speech(
                    text=chunk,
                    voice=voice,
                    speaking_rate=speaking_rate,
                    audio_format=audio_format,
                    use_cache=use_cache
                )
                yield audio_content
                logger.debug(f"✅ Fragmento {i+1}/{len(text_chunks)} procesado por OpenAI TTS")
            except Exception as e:
                logger.error(f"❌ Error procesando fragmento {i+1} con OpenAI TTS: {e}")
                continue
    
    def get_cache_stats(self) -> Optional[Dict[str, Any]]:
        if self.cache:
            return self.cache.get_stats()
        return None
    
    def clear_cache(self):
        if self.cache:
            self.cache.clear_expired()

# --- Implementación de KokoroTTSService (Específico para servidor Kokoro ONNX) ---
class KokoroTTSService(TTSService):
    """
    Implementación de TTSService para el servidor Kokoro ONNX del usuario.
    Se conecta a un servidor local que expone un endpoint /tts.
    """
    DEFAULT_VOICE = "ef_dora"
    
    def __init__(self, cache_enabled: bool = True, cache_dir: Optional[str] = None, api_base: Optional[str] = None):
        # Si el usuario no proporcionó un api_base, intentar autodescubrimiento
        if not api_base or "localhost" in api_base or "127.0.0.1" in api_base:
            base_url = api_base or "http://localhost:8011"
            
            # Si estamos en Docker, intentar detectar el mejor endpoint para Kokoro
            if os.path.exists("/.dockerenv"):
                import socket
                # Prioridad 1: Intentar usar el nombre de servicio 'kokoro-tts' (estándar en este proyecto)
                try:
                    socket.gethostbyname("kokoro-tts")
                    self.api_base = base_url.replace("localhost", "kokoro-tts").replace("127.0.0.1", "kokoro-tts").replace("host.docker.internal", "kokoro-tts")
                    logger.info(f"🐳 Detectado servicio 'kokoro-tts' en red Docker. Usando: {self.api_base}")
                except:
                    # Fallback 2: host.docker.internal (Mac/Win o Linux con extra_hosts)
                    self.api_base = base_url.replace("localhost", "host.docker.internal").replace("127.0.0.1", "host.docker.internal")
                    logger.info(f"🔄 Usando fallback host.docker.internal para Kokoro: {self.api_base}")
            else:
                self.api_base = base_url
        else:
            # Respetar el api_base manual si no es localhost
            self.api_base = api_base
            
        # Safeguard: Si es Kokoro y apunta al puerto 8009 obsoleto, redirigir al 8011
        if ":8009" in self.api_base:
            self.api_base = self.api_base.replace(":8009", ":8011")
            logger.info(f"🔄 [SAFEGUARD] Puerto de Kokoro redirigido de 8009 a 8011: {self.api_base}")

        if not self.api_base.endswith("/tts") and not self.api_base.endswith("/tts/"):
            if self.api_base.endswith("/"):
                self.api_base += "tts"
            else:
                self.api_base += "/tts"
        
        self.cache: Optional[TTSCache] = None
        if cache_enabled:
            self.cache = TTSCache(cache_dir=cache_dir)
            
        logger.info(f"✅ Cliente de Kokoro TTS inicializado con api_base '{self.api_base}'.")

    async def synthesize_speech(
        self,
        text: str,
        voice: Optional[str] = None,
        speaking_rate: float = 1.0,
        pitch: float = 0.0,
        volume_gain_db: float = 0.0,
        audio_format: str = "wav",
        use_cache: bool = True
    ) -> bytes:
        if not text or not text.strip():
            return b""
        
        # Kokoro ONNX siempre devuelve WAV
        effective_format = "wav"
        
        # Verificar caché primero
        if use_cache and self.cache and text:
            cached_audio = self.cache.get(text, voice or self.DEFAULT_VOICE, speaking_rate, effective_format)
            if cached_audio:
                logger.info(f"✅ Audio recuperado de caché ({len(cached_audio)} bytes)")
                return cached_audio

        import httpx
        try:
            # Payload según el servidor propocionado por el usuario
            payload = {
                "text": text,
                "voice": (voice or self.DEFAULT_VOICE).strip(),
                "speed": speaking_rate,
                "lang": "es" # Por defecto español
            }
            
            logger.debug(f"🚀 Enviando petición a Kokoro: {self.api_base} | voice={payload['voice']}")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(self.api_base, json=payload, timeout=90.0)
                
                if response.status_code != 200:
                    logger.error(f"❌ Kokoro TTS devolvió error {response.status_code}: {response.text}")
                    response.raise_for_status()
                
                audio_content = response.content
            
            # Guardar en caché
            if use_cache and self.cache and text:
                self.cache.set(text, voice or self.DEFAULT_VOICE, speaking_rate, effective_format, audio_content)
                
            logger.info(f"✅ Audio generado exitosamente con Kokoro TTS: {len(audio_content)} bytes")
            return audio_content
        except Exception as e:
            logger.error(f"❌ Error en síntesis de voz de Kokoro TTS en {self.api_base}: {e}")
            raise Exception(f"Error en Kokoro TTS: {e}")

    async def synthesize_speech_streaming(
        self,
        text_chunks: List[str],
        voice: Optional[str] = None,
        speaking_rate: float = 1.0,
        audio_format: str = "wav",
        use_cache: bool = True
    ) -> AsyncGenerator[bytes, None]:
        for i, chunk in enumerate(text_chunks):
            if not chunk or not chunk.strip():
                continue
            try:
                audio_content = await self.synthesize_speech(
                    text=chunk,
                    voice=voice,
                    speaking_rate=speaking_rate,
                    audio_format=audio_format,
                    use_cache=use_cache
                )
                yield audio_content
                logger.debug(f"✅ Fragmento {i+1}/{len(text_chunks)} procesado por Kokoro TTS")
            except Exception as e:
                logger.error(f"❌ Error procesando fragmento {i+1} con Kokoro TTS: {e}")
                continue
    
    def get_cache_stats(self) -> Optional[Dict[str, Any]]:
        if self.cache:
            return self.cache.get_stats()
        return None
    
    def clear_cache(self):
        if self.cache:
            self.cache.clear_expired()
# --- Implementación de CoquiTTSService ---
class CoquiTTSService(TTSService):
    """
    Implementación de TTSService para Coqui TTS (XTTS v2).
    Se conecta a un servidor local que expone un endpoint /tts.
    """
    DEFAULT_VOICE = "Ana Maria"
    
    def __init__(self, cache_enabled: bool = True, cache_dir: Optional[str] = None, api_base: Optional[str] = None):
        # Asegurarnos de que el endpoint termine en /tts si es el servidor estándar de XTTS
        self.api_base = api_base or "http://localhost:8006"

        # Si estamos en Docker, intentar detectar el mejor endpoint para Coqui
        if os.path.exists("/.dockerenv") and any(x in self.api_base for x in ["localhost", "127.0.0.1", "host.docker.internal"]):
            import socket
            # Prioridad 1: Intentar usar el nombre de servicio 'coqui-tts'
            try:
                socket.gethostbyname("coqui-tts")
                self.api_base = self.api_base.replace("localhost", "coqui-tts").replace("127.0.0.1", "coqui-tts").replace("host.docker.internal", "coqui-tts")
                logger.info(f"🐳 Detectado servicio 'coqui-tts' en red Docker. Usando: {self.api_base}")
            except:
                # Fallback 2: host.docker.internal (Mac/Win)
                if "localhost" in self.api_base or "127.0.0.1" in self.api_base:
                    self.api_base = self.api_base.replace("localhost", "host.docker.internal").replace("127.0.0.1", "host.docker.internal")
                    logger.info(f"🔄 Usando fallback host.docker.internal para Coqui: {self.api_base}")

        if not self.api_base.endswith("/tts") and not self.api_base.endswith("/tts/"):

            if self.api_base.endswith("/"):
                self.api_base += "tts"
            else:
                self.api_base += "/tts"
        
        self.cache: Optional[TTSCache] = None
        if cache_enabled:
            self.cache = TTSCache(cache_dir=cache_dir)
            
        logger.info(f"✅ Cliente de Coqui TTS inicializado con api_base '{self.api_base}'.")

    async def synthesize_speech(
        self,
        text: str,
        voice: Optional[str] = None,
        speaking_rate: float = 1.0,
        pitch: float = 0.0,
        volume_gain_db: float = 0.0,
        audio_format: str = "wav",
        use_cache: bool = True
    ) -> bytes:
        if not text or not text.strip():
            logger.warning("⚠️ Texto vacío recibido por Coqui TTS. Omitiendo síntesis.")
            return b""
        
        # Verificar caché primero
        if use_cache and self.cache and text:
            cached_audio = self.cache.get(text, voice or self.DEFAULT_VOICE, speaking_rate, audio_format)
            if cached_audio:
                logger.info(f"✅ Audio recuperado de caché ({len(cached_audio)} bytes)")
                return cached_audio

        import httpx
        try:
            # Payload estándar para servidores XTTS v2 / Coqui local
            payload = {
                "text": text,
                "speaker_id": (voice or self.DEFAULT_VOICE).strip(),
                "language": "es" # Forzado a español para este servicio
            }
            
            logger.debug(f"DEBUG Coqui TTS: Enviando petición a {self.api_base} con payload: {payload}")
            
            async with httpx.AsyncClient() as client:
                # El timeout debe ser generoso ya que generar audio puede tomar tiempo
                response = await client.post(self.api_base, json=payload, timeout=90.0)
                
                if response.status_code != 200:
                    logger.error(f"❌ Coqui TTS devolvió error {response.status_code}: {response.text}")
                    
                response.raise_for_status()
                audio_content = response.content
            
            # Guardar en caché
            if use_cache and self.cache and text:
                self.cache.set(text, voice or self.DEFAULT_VOICE, speaking_rate, audio_format, audio_content)
                
            logger.info(f"✅ Audio generado exitosamente con Coqui TTS: {len(audio_content)} bytes")
            return audio_content
        except Exception as e:
            logger.error(f"❌ Error en síntesis de voz de Coqui TTS: {e}")
            raise Exception(f"Error en Coqui TTS: {e}")

    async def synthesize_speech_streaming(
        self,
        text_chunks: List[str],
        voice: Optional[str] = None,
        speaking_rate: float = 1.0,
        audio_format: str = "wav",
        use_cache: bool = True
    ) -> AsyncGenerator[bytes, None]:
        for i, chunk in enumerate(text_chunks):
            if not chunk or not chunk.strip():
                continue
            try:
                audio_content = await self.synthesize_speech(
                    text=chunk,
                    voice=voice,
                    speaking_rate=speaking_rate,
                    audio_format=audio_format,
                    use_cache=use_cache
                )
                yield audio_content
                logger.debug(f"✅ Fragmento {i+1}/{len(text_chunks)} procesado por Coqui TTS")
            except Exception as e:
                logger.error(f"❌ Error procesando fragmento {i+1} con Coqui TTS: {e}")
                continue
    
    def get_cache_stats(self) -> Optional[Dict[str, Any]]:
        if self.cache:
            return self.cache.get_stats()
        return None
    
    def clear_cache(self):
        if self.cache:
            self.cache.clear_expired()

# --- TTSServiceFactory ---

# --- TTSServiceFactory ---
class TTSServiceFactory:
    """
    Fábrica para obtener instancias de TTSService.
    """
    
    _instances: Dict[str, TTSService] = {} # Para mantener singletons por tipo de servicio
    
    @staticmethod
    async def get_service(
        provider: str, 
        cache_enabled: bool = True, 
        cache_dir: Optional[str] = None,
        api_key_name: Optional[str] = None,
        region: Optional[str] = None, # Para Azure
        account_id: Optional[uuid.UUID] = None, # Para obtener secretos del usuario
        api_base: Optional[str] = None, # Para APIs locales o compatibles
        model: Optional[str] = None # Para APIs locales o compatibles
    ) -> TTSService:
        """
        Obtiene una instancia del servicio TTS especificado.
        
        Args:
            provider: Nombre del proveedor de TTS (ej: "google", "azure")
            cache_enabled: Si se debe habilitar el caché
            cache_dir: Directorio para el caché (None para usar default)
            api_key_name: Nombre de la clave API en UserSecret (si aplica).
            region: Región de Azure (si aplica).
            account_id: ID de la cuenta para recuperar secretos específicos del usuario.
            api_base: URL base para servicios TTS locales/OpenAI.
            model: Modelo de TTS a utilizar.
            
        Returns:
            Una instancia de TTSService
            
        Raises:
            ValueError: Si el proveedor no es soportado
        """
        provider_lower = provider.lower()
        
        # Crear una clave única para la instancia basada en la configuración
        instance_key = f"{provider_lower}-{cache_enabled}-{cache_dir}-{api_key_name}-{region}-{account_id}-{api_base}-{model}"
        
        if instance_key not in TTSServiceFactory._instances:
            # Recuperar API Key si es necesario
            api_key = None
            
            # Si no se proporciona api_key_name, intentar inferirlo por el proveedor
            if not api_key_name:
                if provider_lower == "azure":
                    api_key_name = "AZURE_TTS_KEY"
                elif provider_lower == "openai" or provider_lower == "openai-compatible":
                    api_key_name = "OPENAI_API_KEY"
                elif provider_lower == "google":
                    api_key_name = "GOOGLE_API_KEY"

            if api_key_name and account_id:
                async with SessionLocal() as db:
                    secret_repo = SecretRepository(db)
                    api_key = await secret_repo.get_decrypted_secret(account_id, api_key_name)
                    if not api_key:
                        logger.warning(f"⚠️ API Key '{api_key_name}' no encontrada para la cuenta {account_id}.")
            
            if provider_lower == "google":
                TTSServiceFactory._instances[instance_key] = GoogleTTSService(
                    cache_enabled=cache_enabled, 
                    cache_dir=cache_dir,
                    api_key=api_key
                )
            elif provider_lower == "azure":
                TTSServiceFactory._instances[instance_key] = AzureTTSService(
                    cache_enabled=cache_enabled,
                    cache_dir=cache_dir,
                    api_key=api_key,
                    region=region if region else settings.azure_speech_region # Usar la región de settings si no se especifica
                )
            elif provider_lower in ["openai", "openai-compatible"]:
                # Si el modelo es "kokoro", usar el servicio dedicado de Kokoro ya que su API es única
                if model and "kokoro" in model.lower():
                    TTSServiceFactory._instances[instance_key] = KokoroTTSService(
                        cache_enabled=cache_enabled,
                        cache_dir=cache_dir,
                        api_base=api_base
                    )
                else:
                    TTSServiceFactory._instances[instance_key] = OpenAITTSService(
                        cache_enabled=cache_enabled,
                        cache_dir=cache_dir,
                        api_key=api_key,
                        api_base=api_base,
                        model=model
                    )
            elif provider_lower == "kokoro":
                TTSServiceFactory._instances[instance_key] = KokoroTTSService(
                    cache_enabled=cache_enabled,
                    cache_dir=cache_dir,
                    api_base=api_base
                )
            elif provider_lower == "coquitts" or provider_lower == "coqui":
                TTSServiceFactory._instances[instance_key] = CoquiTTSService(
                    cache_enabled=cache_enabled,
                    cache_dir=cache_dir,
                    api_base=api_base
                )
            else:
                raise ValueError(f"Proveedor de TTS '{provider}' no soportado.")
                
        return TTSServiceFactory._instances[instance_key]

# Instancia global del cliente (singleton)
_tts_client: Optional[TTSService] = None


async def get_tts_client(
    provider: str = "google", 
    cache_enabled: bool = True, 
    cache_dir: Optional[str] = None,
    api_key_name: Optional[str] = None,
    region: Optional[str] = None,
    account_id: Optional[uuid.UUID] = None,
    api_base: Optional[str] = None,
    model: Optional[str] = None
) -> TTSService:
    """
    Obtiene la instancia global del cliente TTS.
    
    Args:
        provider: Nombre del proveedor de TTS (ej: "google", "azure")
        cache_enabled: Si se debe habilitar el caché
        cache_dir: Directorio para el caché
        api_key_name: Nombre de la clave API en UserSecret (si aplica).
        region: Región de Azure (si aplica).
        account_id: ID de la cuenta para recuperar secretos específicos del usuario.
        api_base: URL base para servicios TTS locales/OpenAI.
        
    Returns:
            Instancia de TTSService
    """
    global _tts_client
    # Si no se especifica un proveedor, o si el proveedor es el mismo que el cliente global
    # y la configuración es la misma, devolver la instancia global.
    # Esto es una simplificación, en un sistema más complejo se podría querer
    # un singleton por cada combinación de proveedor/configuración.
    # Obtener el tipo de servicio esperado según el proveedor
    expected_class = None
    p_lower = provider.lower()
    if p_lower in ["google", "google-tts"]:
        from core.tts_manager import GoogleTTSService
        expected_class = GoogleTTSService
    elif p_lower in ["azure", "azure-tts"]:
        from core.tts_manager import AzureTTSService
        expected_class = AzureTTSService
    elif p_lower in ["openai", "openai-compatible"]:
        if model and "kokoro" in model.lower():
            from core.tts_manager import KokoroTTSService
            expected_class = KokoroTTSService
        else:
            from core.tts_manager import OpenAITTSService
            expected_class = OpenAITTSService
    elif p_lower == "kokoro":
        from core.tts_manager import KokoroTTSService
        expected_class = KokoroTTSService
    elif p_lower in ["coquitts", "coqui"]:
        from core.tts_manager import CoquiTTSService
        expected_class = CoquiTTSService

    # Si no hay cliente, o es de otro tipo, o cambió la config
    if _tts_client is None or not isinstance(_tts_client, expected_class) or getattr(_tts_client, "api_base", None) != api_base or getattr(_tts_client, "model", None) != model:
        _tts_client = await TTSServiceFactory.get_service(
            provider=provider, 
            cache_enabled=cache_enabled, 
            cache_dir=cache_dir,
            api_key_name=api_key_name,
            region=region,
            account_id=account_id,
            api_base=api_base,
            model=model
        )
    return _tts_client


# Funciones de conveniencia (adaptadas para usar la fábrica)
async def generate_speech(
    text: str,
    provider: str = "google",
    voice: Optional[str] = None,
    speaking_rate: float = 1.0,
    audio_format: str = "mp3",
    use_cache: bool = True,
    api_key_name: Optional[str] = None,
    region: Optional[str] = None,
    account_id: Optional[uuid.UUID] = None,
    api_base: Optional[str] = None,
    model: Optional[str] = None
) -> bytes:
    """
    Función de conveniencia para generar audio a partir de texto.
    
    Args:
        text: Texto a convertir
        provider: Proveedor de TTS a usar
        voice: Código de voz
        speaking_rate: Velocidad de habla
        audio_format: Formato de audio
        use_cache: Si se debe usar el caché
        api_key_name: Nombre de la clave API en UserSecret (si aplica).
        region: Región de Azure (si aplica).
        account_id: ID de la cuenta para recuperar secretos específicos del usuario.
        api_base: URL base para servicios TTS locales/OpenAI.
        
    Returns:
        Bytes del audio generado
    """
    client = await get_tts_client(
        provider=provider, 
        api_key_name=api_key_name, 
        region=region, 
        account_id=account_id,
        api_base=api_base,
        model=model
    )
    return await client.synthesize_speech(
        text=text,
        voice=voice,
        speaking_rate=speaking_rate,
        audio_format=audio_format,
        use_cache=use_cache
    )


async def generate_speech_streaming(
    text_chunks: List[str],
    provider: str = "google",
    voice: Optional[str] = None,
    speaking_rate: float = 1.0,
    audio_format: str = "mp3",
    use_cache: bool = True,
    api_key_name: Optional[str] = None,
    region: Optional[str] = None,
    account_id: Optional[uuid.UUID] = None,
    api_base: Optional[str] = None,
    model: Optional[str] = None
) -> AsyncGenerator[bytes, None]:
    """
    Función de conveniencia para generar audio en streaming.
    
    Args:
        text_chunks: Lista de fragmentos de texto
        provider: Proveedor de TTS a usar
        voice: Código de voz
        speaking_rate: Velocidad de habla
        audio_format: Formato de audio
        use_cache: Si se debe usar el caché
        api_key_name: Nombre de la clave API en UserSecret (si aplica).
        region: Región de Azure (si aplica).
        account_id: ID de la cuenta para recuperar secretos específicos del usuario.
        api_base: URL base para servicios TTS locales/OpenAI.
        model: Modelo de TTS a utilizar.
        
    Yields:
        Bytes de audio para cada fragmento
    """
    client = await get_tts_client(
        provider=provider, 
        api_key_name=api_key_name, 
        region=region, 
        account_id=account_id,
        api_base=api_base,
        model=model
    )
    async for chunk in client.synthesize_speech_streaming(
        text_chunks=text_chunks,
        voice=voice,
        speaking_rate=speaking_rate,
        audio_format=audio_format,
        use_cache=use_cache
    ):
        yield chunk
