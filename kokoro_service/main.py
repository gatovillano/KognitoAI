#!/usr/bin/env python3

import io
import re
import wave
import numpy as np
import edge_tts
import asyncio
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from kokoro_onnx import Kokoro
from typing import AsyncGenerator

app = FastAPI(title="Unified Streaming TTS Service")

# Configuracion
MODELS_DIR = Path("/opt/kokoro")
MODEL_PATH = MODELS_DIR / "kokoro-v1.0.onnx"
VOICES_PATH = MODELS_DIR / "voices-v1.0.bin"

# Voces predeterminadas
DEFAULT_VOICE = "ef_dora"
DEFAULT_LANG = "es"
DEFAULT_SPEED = 1.0

# Inicializar modelo Kokoro
print("🚀 Cargando modelo Kokoro ONNX...")
if not MODEL_PATH.exists():
    print(f"⚠️ ADVERTENCIA: No se encuentra el modelo en {MODEL_PATH}. Kokoro estará deshabilitado.")
    kokoro = None
else:
    try:
        kokoro = Kokoro(str(MODEL_PATH), str(VOICES_PATH))
        print("✅ Modelo Kokoro cargado correctamente")
    except Exception as e:
        print(f"❌ Error cargando Kokoro: {e}")
        kokoro = None

class TTSRequest(BaseModel):
    text: str
    voice: str = DEFAULT_VOICE
    speed: float = DEFAULT_SPEED
    lang: str = DEFAULT_LANG

def split_text(text: str):
    """Divide el texto en frases usando puntuación."""
    sentences = re.split(r'([.!?]+[\s\n]+)', text)
    chunks = []
    current = ""
    for i in range(0, len(sentences), 2):
        s = sentences[i]
        d = sentences[i+1] if i+1 < len(sentences) else ""
        full = (s + d).strip()
        if not full: continue
        if len(current) + len(full) < 200: # Trozos pequeños para streaming rápido
            current += (" " if current else "") + full
        else:
            if current: chunks.append(current)
            current = full
    if current: chunks.append(current)
    return chunks

async def edge_stream_generator(text: str, voice: str, speed: float) -> AsyncGenerator[bytes, None]:
    """Generador para streaming desde Edge-TTS."""
    # Ajustar velocidad para Edge (+0%, -20%, etc.)
    rate = int((speed - 1.0) * 100)
    rate_str = f"{rate:+d}%"
    
    communicate = edge_tts.Communicate(text, voice, rate=rate_str)
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            yield chunk["data"]

async def kokoro_stream_generator(text: str, voice: str, speed: float, lang: str) -> AsyncGenerator[bytes, None]:
    """Generador para Kokoro (concatena frases en un solo WAV para evitar problemas de headers)."""
    if not kokoro:
        raise Exception("Modelo Kokoro no disponible")
    
    chunks = split_text(text)
    all_samples = []
    final_sample_rate = 24000
    
    for chunk in chunks:
        # Generar audio de la frase
        samples, sample_rate = kokoro.create(
            chunk, 
            voice=voice, 
            speed=float(speed), 
            lang=lang
        )
        all_samples.append(samples)
        final_sample_rate = sample_rate
    
    if not all_samples:
        return

    # Combinar todos los fragmentos
    combined_samples = np.concatenate(all_samples)
    
    # Convertir a WAV en memoria (un solo archivo completo)
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(final_sample_rate)
        # Normalizar y convertir a int16
        audio_int16 = (combined_samples * 32767).astype(np.int16)
        wav_file.writeframes(audio_int16.tobytes())
    
    yield wav_buffer.getvalue()

@app.get("/")
async def root():
    return {"status": "online", "engine": "Unified Streaming (Kokoro + Edge)"}

@app.get("/voices")
async def list_voices():
    k_voices = kokoro.get_voices() if kokoro else []
    # Solo mostramos algunas de Edge para no saturar, pero admite cualquiera de Edge
    e_voices = ["es-MX-DaliaNeural", "es-MX-JorgeNeural", "es-ES-AlvaroNeural", "en-US-AriaNeural"]
    return {"voices": k_voices + e_voices}

@app.post("/tts")
async def generate_speech(request: TTSRequest):
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Texto vacío")

    # Decidir motor
    is_edge = "-" in request.voice and (request.voice.startswith("es-") or request.voice.startswith("en-"))
    
    if is_edge:
        print(f"📡 Streaming Edge-TTS: {request.voice}")
        return StreamingResponse(
            edge_stream_generator(request.text, request.voice, request.speed),
            media_type="audio/mpeg"
        )
    else:
        # Autodetectar idioma para Kokoro si es necesario
        effective_lang = request.lang
        v = request.voice.lower()
        if effective_lang == DEFAULT_LANG:
            if v.startswith("ef"): effective_lang = "es"
            elif v.startswith("a") or v.startswith("e"): effective_lang = "en-us"
            elif v.startswith("b"): effective_lang = "en-gb"

        print(f"🏠 Streaming Kokoro: {request.voice} ({effective_lang})")
        return StreamingResponse(
            kokoro_stream_generator(request.text, request.voice, request.speed, effective_lang),
            media_type="audio/wav"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8011)
