---
## 25-10-25 Solución definitiva para la autenticación WebSocket de transcripción de audio

Descripción general:
Se implementó la solución definitiva para el problema de autenticación (error 403) en el endpoint WebSocket de transcripción (`/ws/transcribe/{account_id}`). La causa raíz fue una discrepancia en cómo se manejaba la autenticación en comparación con el endpoint de chat funcional (`/ws/{user_id}`). La solución consistió en replicar la lógica de autenticación directa del endpoint de chat dentro del endpoint de transcripción, manejando la extracción y validación del token de los `query_params` directamente en la función.

- **Replicación de lógica de autenticación**: El endpoint `websocket_transcribe` en `api/chat.py` ahora implementa directamente la lógica de extracción del token de los `query_params`, decodificación del JWT, y verificación del `account_id` (comparándolo con el `account_id` de la URL), de manera idéntica a cómo lo hace el `websocket_endpoint` en `api/main.py`.
- **Manejo de excepciones mejorado**: Las excepciones relacionadas con la falta de token, token inválido/expirado o conflicto de ID de usuario se manejan explícitamente dentro de la función, cerrando la conexión WebSocket con el código de estado y la razón adecuados.
- **Eliminación de logs de depuración**: Se eliminaron los logs de depuración temporales añadidos en `api/chat.py` y `utils/security.py` una vez que se identificó y corrigió el problema.
- **Coherencia y funcionalidad**: Esta implementación asegura que la autenticación para la transcripción de audio sea robusta y coherente con el resto del sistema, resolviendo el error 403 y permitiendo que la funcionalidad de transcripción opere correctamente.
---
## 25-10-25 Solución al error "EBML header parsing failed" en StreamingTranscriber

Descripción general:
Se ha corregido un error en la clase `StreamingTranscriber` en [`utils/audio_transcriber.py`](utils/audio_transcriber.py) que causaba fallos de decodificación de `ffmpeg` con el mensaje "EBML header parsing failed" al procesar fragmentos de audio `webm` en streaming. La solución implementada acumula los bytes de audio en un búfer antes de intentar la decodificación, asegurando que `pydub` reciba un flujo de audio completo y válido.

- **Modificación de `StreamingTranscriber.__init__`**: Se reemplazó `self.audio_buffer` por `self.raw_audio_bytes_buffer` (un objeto `BytesIO`) para almacenar los bytes crudos del audio. Se añadió `self.file_format` para guardar el formato del archivo.
- **Modificación de `StreamingTranscriber.process_audio_chunk`**: La función ahora acumula los `audio_chunk_bytes` en `self.raw_audio_bytes_buffer`. La decodificación y transcripción con `pydub` y `Whisper` solo se realiza cuando la duración acumulada del audio alcanza `self.chunk_length_s`. Se añadió una lógica para limpiar el búfer después de una transcripción exitosa o si el búfer crece demasiado sin nuevo texto.
- **Modificación de `StreamingTranscriber.finalize_transcription`**: Se ajustó para usar el `self.raw_audio_bytes_buffer` acumulado para la decodificación final y se reseteó `self.file_format`.
---
## 25-10-25 Solución al `KeyError: 'bytes'` en WebSocket de transcripción

Descripción general:
Se ha corregido el `KeyError: 'bytes'` que ocurría en la función `websocket_transcribe` en [`api/main.py`](api/main.py) al intentar acceder a la clave `'bytes'` de un mensaje de WebSocket que no la contenía. Esto sucedía porque `websocket.receive_bytes()` esperaba un mensaje binario, pero el cliente podía enviar otros tipos de mensajes. La solución implementada ahora verifica el tipo de mensaje recibido antes de intentar acceder a los datos.

- **Modificación de `websocket_transcribe`**: La función ahora utiliza `await websocket.receive()` para obtener el mensaje completo del WebSocket.
- **Manejo de tipos de mensajes**: Se añadió una lógica para verificar el `message["type"]`. Si el tipo es `"websocket.receive"` y contiene la clave `"bytes"`, se procesan los datos binarios. Se añadió un manejo para mensajes de texto y se registra un aviso para tipos de mensajes inesperados.
- **Manejo de desconexión**: La lógica de finalización de la transcripción se movió al bloque `if message["type"] == "websocket.disconnect"` para asegurar que se ejecute cuando el cliente se desconecta limpiamente.
---
## 25-10-25 Mejora en el manejo de streaming de audio WebM

Descripción general:
Se han añadido parámetros de configuración a `ffmpeg` a través de `pydub` en la clase `StreamingTranscriber` en [`utils/audio_transcriber.py`](utils/audio_transcriber.py) para mejorar la robustez en la decodificación de flujos de audio WebM incompletos o con problemas de encabezado. Esto aborda el error `CouldntDecodeError` y los mensajes de `ffmpeg` como "EBML header parsing failed" y "Inner protocol failed to seekback end".

- **Parámetros `ffmpeg` añadidos**: Se incluyeron los parámetros `"-probesize", "32", "-analyzeduration", "0"` en las llamadas a `AudioSegment.from_file` dentro de `process_audio_chunk` y `finalize_transcription`. Estos parámetros reducen la cantidad de datos que `ffmpeg` intenta sondear y analizar al inicio del flujo, lo que es beneficioso para el procesamiento de streaming donde los fragmentos pueden no tener encabezados completos o ser muy pequeños.
---
## 25-10-25 Implementación de remuestreo de audio y logging detallado en StreamingTranscriber

Descripción general:
Se ha implementado el remuestreo de audio de 48kHz a 16kHz en la función `_resample_audio` de la clase `StreamingTranscriber` en [`utils/audio_transcriber.py`](utils/audio_transcriber.py). Esto soluciona el problema de que el modelo Whisper no transcribía debido a una frecuencia de muestreo incorrecta. Además, se añadió logging detallado para verificar la correcta creación y remuestreo del `AudioSegment`.

- **Remuestreo de audio**: La función `_resample_audio` ahora convierte el `numpy array` de audio a un `AudioSegment` de `pydub`, lo remuestrea a 16kHz y lo convierte de nuevo a un `numpy array` `float32`.
- **Logging detallado**: Se añadió un mensaje de log al final de la función `_resample_audio` para confirmar que el remuestreo se realizó correctamente y mostrar el tamaño del array resultante.
---
## 25-10-25 Ajuste de parámetros VAD en StreamingTranscriber

Descripción general:
Se ha ajustado el parámetro `min_silence_duration_ms` en la clase `StreamingTranscriber` en [`utils/audio_transcriber.py`](utils/audio_transcriber.py) para que sea menos restrictivo. Esto se hizo para abordar el problema de que el filtro VAD (Voice Activity Detection) estaba eliminando todo el audio, impidiendo la transcripción, incluso después de implementar el remuestreo.

- **`min_silence_duration_ms` ajustado**: El valor de `min_silence_duration_ms` se ha cambiado de 500ms a 1000ms. Este cambio busca permitir que el VAD detecte segmentos de voz más largos, evitando que se descarten fragmentos de audio válidos.
---
## 25-10-25 Solución robusta para la transcodificación de WebM en StreamingTranscriber

Descripción general:
Se ha implementado una solución más robusta para la transcodificación de audio WebM a PCM en la clase `StreamingTranscriber` en [`utils/audio_transcriber.py`](utils/audio_transcriber.py). Esto aborda los errores persistentes de `CouldntDecodeError` y "EBML header parsing failed" que ocurrían al intentar decodificar flujos WebM incompletos o con problemas de encabezado directamente desde un `BytesIO`. La nueva implementación utiliza archivos temporales para la transcodificación con `ffmpeg`, lo que permite que `ffmpeg` trate el flujo como un archivo completo y resuelva los problemas de encabezado y búsqueda.

- **Uso de archivos temporales para transcodificación**: La función `_transcode_webm_to_raw_pcm` ahora escribe el `webm` acumulado en un archivo temporal de entrada. Luego, `ffmpeg` transcodifica este archivo temporal a un archivo temporal de salida `raw` PCM a 16kHz. Finalmente, se lee el contenido del archivo PCM y se devuelven los datos.
- **Importación de `os`**: Se añadió la importación del módulo `os` para manejar la creación y eliminación de archivos temporales.
---
## 25-10-25 Integración de transcodificación robusta en `finalize_transcription`

Descripción general:
Se ha modificado la función `finalize_transcription` en la clase `StreamingTranscriber` en [`utils/audio_transcriber.py`](utils/audio_transcriber.py) para utilizar la función `_transcode_webm_to_raw_pcm`. Esto asegura que el audio restante en el búfer se transcodifique de manera robusta a PCM antes de ser procesado por el modelo Whisper, resolviendo los problemas de decodificación que persistían en la fase de finalización.

- **Uso de `_transcode_webm_to_raw_pcm`**: La función `finalize_transcription` ahora invoca `_transcode_webm_to_raw_pcm` para obtener los datos PCM del audio acumulado, garantizando un procesamiento consistente y fiable.
- **Logging adicional**: Se añadió un mensaje de advertencia si no se obtienen datos PCM después de la transcodificación en `finalize_transcription`.
---
## 25-10-25 Refactorización de transcodificación de audio en StreamingTranscriber

Descripción general:
Se ha refactorizado la clase `StreamingTranscriber` en [`utils/audio_transcriber.py`](utils/audio_transcriber.py) para eliminar la dependencia de `ffmpeg` y archivos temporales en la transcodificación de audio WebM a PCM. Ahora se utiliza `pydub` directamente para un procesamiento más eficiente y robusto en entornos de streaming.

- **Refactorización de `_transcode_webm_to_raw_pcm`**: Se modificó la función para usar `pydub` directamente, eliminando la necesidad de `ffmpeg` y archivos temporales. Ahora decodifica el audio desde un `BytesIO` y exporta los datos PCM raw.
- **Actualización de `process_audio_chunk`**: Se ajustó esta función para utilizar la nueva implementación de `_transcode_webm_to_raw_pcm`, lo que simplifica el flujo de procesamiento de audio.
- **Eliminación de importaciones innecesarias**: Se eliminaron las importaciones de `subprocess` y `tempfile` ya que ya no son utilizadas en el archivo.
---
## 25-10-25 Mejora en la robustez de transcodificación de WebM en StreamingTranscriber

Descripción general:
Se han añadido parámetros de configuración a `ffmpeg` a través de `pydub` en la clase `StreamingTranscriber` en [`utils/audio_transcriber.py`](utils/audio_transcriber.py) para mejorar la robustez en la decodificación de flujos de audio WebM incompletos o con problemas de encabezado. Esto aborda el error `CouldntDecodeError` y los mensajes de `ffmpeg` como "EBML header parsing failed" y "Inner protocol failed to seekback end".

- **Parámetros `ffmpeg` añadidos**: Se incluyeron los parámetros `"-probesize", "32", "-analyzeduration", "0"` en las llamadas a `AudioSegment.from_file` dentro de `_transcode_webm_to_raw_pcm`. Estos parámetros reducen la cantidad de datos que `ffmpeg` intenta sondear y analizar al inicio del flujo, lo que es beneficioso para el procesamiento de streaming donde los fragmentos pueden no tener encabezados completos o ser muy pequeños.
---
## 25-10-25 Reversión y mejora de la transcodificación de WebM en StreamingTranscriber

Descripción general:
Se ha revertido la estrategia de transcodificación de audio WebM a PCM en la clase `StreamingTranscriber` en [`utils/audio_transcriber.py`](utils/audio_transcriber.py) para volver a utilizar archivos temporales con `ffmpeg` directamente. Esta decisión se tomó debido a problemas persistentes de decodificación (`EBML header parsing failed`, `Inner protocol failed to seekback end`) al intentar procesar fragmentos de `webm` en streaming directamente con `pydub`. Se han incluido parámetros de robustez directamente en el comando `ffmpeg` para asegurar su correcta aplicación.

- **Reversión a archivos temporales**: La función `_transcode_webm_to_raw_pcm` ahora utiliza archivos temporales para escribir los datos `webm` y luego invoca `ffmpeg` para transcodificarlos a `raw` PCM.
- **Parámetros de robustez en `ffmpeg`**: Se han añadido los parámetros `"-probesize", "32"`, `"-analyzeduration", "0"` y `"-fflags", "+genpts"` directamente al comando `ffmpeg`. Estos parámetros ayudan a `ffmpeg` a manejar flujos de entrada incompletos o problemáticos, mejorando la generación de marcas de tiempo y la detección de encabezados.
- **Actualización de importaciones**: Se han reintroducido las importaciones de `subprocess` y `tempfile` que son necesarias para esta estrategia.