# Dockerfile
# Este Dockerfile construye la imagen para el servicio del BOT de Telegram.
# Es un cliente ligero que se comunica con el backend (servicio 'webapp').

# --- 1. Imagen Base ---
# Usamos una imagen de Python 3.11 slim, que es ligera pero completa.
FROM python:3.11-slim

# --- 2. Variables de Entorno ---
# Configura variables de entorno para un comportamiento óptimo de Python en Docker.
ENV PYTHONDONTWRITEBYTECODE 1  # Evita que Python escriba archivos .pyc, innecesarios en contenedores.
ENV PYTHONUNBUFFERED 1         # Asegura que los logs de Python se envíen directamente a la terminal de Docker.

# --- 3. Dependencias del Sistema ---
# Instala dependencias a nivel de sistema operativo que algunas librerías de Python
# podrían necesitar. `libpq-dev` es para `psycopg`, aunque este servicio no conecta
# directamente a la BD, a veces es necesario para otras sub-dependencias. `ffmpeg` es
# crucial para el procesamiento de audio con `faster-whisper`.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# --- 4. Directorio de Trabajo ---
# Define el directorio de trabajo dentro del contenedor. Todos los comandos
# siguientes se ejecutarán desde esta ruta.
WORKDIR /app

# --- 5. Instalación de Dependencias de Python ---
# Copia SOLO el archivo de requerimientos primero. Esto aprovecha la caché de Docker.
# Si el archivo no cambia, Docker no volverá a ejecutar la instalación,
# haciendo las construcciones futuras mucho más rápidas.
COPY requirements.txt .

# Instala las dependencias de Python definidas en requirements.txt.
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# --- 6. Copia del Código de la Aplicación ---
# Copia todo el resto del código del proyecto al directorio de trabajo del contenedor.
# Esto incluye `main.py`, la carpeta `telegram_bot/`, `utils/`, etc.
COPY . .

# --- 7. Comando de Ejecución ---
# El comando que se ejecutará cuando el contenedor se inicie.
# Le dice a Python que ejecute el archivo `main.py`, que es el punto de
# entrada de nuestro cliente de Telegram.
CMD ["python", "main.py"]

