FROM python:3.12-slim

# Instalar dependencias del sistema (espeak-ng para G2P fallback)
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    espeak-ng \
    libespeak-ng1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/kokoro

# Instalar dependencias Python
RUN pip install --no-cache-dir \
    kokoro-onnx \
    fastapi \
    "uvicorn[standard]" \
    pydantic \
    soundfile \
    edge-tts

# Descargar modelo ONNX cuantizado (Optimizado para CPU) y voces (~100MB + voces)
RUN wget -q -O kokoro-v1.0.onnx \
    https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.int8.onnx && \
    wget -q -O voices-v1.0.bin \
    https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin

# Copiar el servidor (nuestro archivo es main.py)
COPY main.py /opt/kokoro/main.py

# Exponer el puerto configurado en docker-compose.yml
EXPOSE 8011

# CMD ["python3", "main.py"] o directo con uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8011"]
