# utils/google_tts.py

"""
Módulo de utilidad para Text-to-Speech (TTS) usando Google Cloud Text-to-Speech API.

Este módulo proporciona funciones para convertir texto a audio utilizando
la API de Google Cloud Text-to-Speech, con soporte para múltiples voces,
configuraciones de audio y caché de audios generados.

Responsabilidades:
- Generar audio a partir de texto usando Google Cloud TTS
- Manejar múltiples idiomas y voces
- Proporcionar streaming de audio para textos largos
- Gestionar caché de audios para evitar regeneraciones
- Gestionar errores y reintentos
"""

import logging
import os
import hashlib
import json
from typing import Optional, List, AsyncGenerator, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path
from io import BytesIO
import asyncio

from google.cloud import texttospeech
from google.oauth2 import service_account
from google.api_core.exceptions import GoogleAPICallError, RetryError


logger = logging.getLogger(__name__)


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


class GoogleTTSClient:
    """
    Cliente para interactuar con Google Cloud Text-to-Speech API.
    
    Esta clase encapsula la lógica de generación de audio y proporciona
    métodos para convertir texto a voz con diferentes configuraciones,
    incluyendo soporte para caché de audios.
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
    
    def __init__(self, cache_enabled: bool = True, cache_dir: Optional[str] = None):
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
            api_key = os.getenv("GOOGLE_API_KEY")
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


# Instancia global del cliente (singleton)
_tts_client: Optional[GoogleTTSClient] = None


def get_tts_client(cache_enabled: bool = True, cache_dir: Optional[str] = None) -> GoogleTTSClient:
    """
    Obtiene la instancia global del cliente TTS.
    
    Args:
        cache_enabled: Si se debe habilitar el caché
        cache_dir: Directorio para el caché
        
    Returns:
        Instancia de GoogleTTSClient
    """
    global _tts_client
    if _tts_client is None:
        _tts_client = GoogleTTSClient(cache_enabled=cache_enabled, cache_dir=cache_dir)
    return _tts_client


async def generate_speech(
    text: str,
    voice: Optional[str] = None,
    speaking_rate: float = 1.0,
    audio_format: str = "mp3",
    use_cache: bool = True
) -> bytes:
    """
    Función de conveniencia para generar audio a partir de texto.
    
    Args:
        text: Texto a convertir
        voice: Código de voz
        speaking_rate: Velocidad de habla
        audio_format: Formato de audio
        use_cache: Si se debe usar el caché
        
    Returns:
        Bytes del audio generado
    """
    client = get_tts_client()
    return await client.synthesize_speech(
        text=text,
        voice=voice,
        speaking_rate=speaking_rate,
        audio_format=audio_format,
        use_cache=use_cache
    )


async def generate_speech_streaming(
    text_chunks: List[str],
    voice: Optional[str] = None,
    speaking_rate: float = 1.0,
    audio_format: str = "mp3",
    use_cache: bool = True
) -> AsyncGenerator[bytes, None]:
    """
    Función de conveniencia para generar audio en streaming.
    
    Args:
        text_chunks: Lista de fragmentos de texto
        voice: Código de voz
        speaking_rate: Velocidad de habla
        audio_format: Formato de audio
        use_cache: Si se debe usar el caché
        
    Yields:
        Bytes de audio para cada fragmento
    """
    client = get_tts_client()
    async for chunk in client.synthesize_speech_streaming(
        text_chunks=text_chunks,
        voice=voice,
        speaking_rate=speaking_rate,
        audio_format=audio_format,
        use_cache=use_cache
    ):
        yield chunk
