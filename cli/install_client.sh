#!/bin/bash
set -e

echo "=================================================="
echo "    Instalador del Cliente Kognito Sync para Linux"
echo "=================================================="

# 1. Instalar dependencias del sistema si usa Debian/Ubuntu
if [ -f /etc/debian_version ]; then
    echo "Detectado sistema basado en Debian/Ubuntu."
    echo "Instalando python3-tk, python3-venv, python3-pip..."
    sudo apt-get update && sudo apt-get install -y python3-tk python3-venv python3-pip
else
    echo "Sistema no basado en Debian detectado. Por favor, asegúrate de tener instalado python3-tk."
fi

# 2. Configurar directorio de instalación
INSTALL_DIR="$HOME/.local/share/kognito-sync"
echo "Creando directorio de instalación en: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"

# 3. Configurar entorno virtual
echo "Configurando entorno virtual de Python..."
python3 -m venv "$INSTALL_DIR/venv"
source "$INSTALL_DIR/venv/bin/activate"

echo "Instalando paquetes de Python (customtkinter, pystray, watchdog, httpx, pillow)..."
pip install --upgrade pip
pip install customtkinter pystray watchdog httpx pillow

# 4. Copiar código fuente
echo "Copiando archivos del cliente..."
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cp "$DIR/main.py" "$DIR/sync_logic.py" "$DIR/run.sh" "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/run.sh"

# 5. Generar icono oficial usando Python y PIL
echo "Generando icono de aplicación..."
python3 -c "
from PIL import Image, ImageDraw
img = Image.new('RGBA', (128, 128), (0, 0, 0, 0))
dc = ImageDraw.Draw(img)
dc.ellipse([16, 16, 112, 112], fill=(59, 130, 246))
dc.ellipse([40, 40, 88, 88], fill=(255, 255, 255))
img.save('$INSTALL_DIR/icon.png')
"

# 6. Crear el lanzador de escritorio (.desktop)
echo "Creando lanzador de escritorio (.desktop)..."
mkdir -p "$HOME/.local/share/applications"

cat <<EOF > "$HOME/.local/share/applications/kognito-sync.desktop"
[Desktop Entry]
Type=Application
Name=Kognito Sync
Comment=Cliente de sincronización de documentos para Kognito AI
Exec=$INSTALL_DIR/run.sh
Icon=$INSTALL_DIR/icon.png
Terminal=false
Categories=Utility;FileTransfer;
StartupNotify=true
EOF

# 7. Crear inicio automático (opcional, al iniciar sesión)
echo "Creando configuración de inicio automático (Autostart)..."
mkdir -p "$HOME/.config/autostart"
cp "$HOME/.local/share/applications/kognito-sync.desktop" "$HOME/.config/autostart/"

echo "=================================================="
echo " ¡INSTALACIÓN COMPLETADA EXITOSAMENTE!"
echo "=================================================="
echo "Ya puedes buscar 'Kognito Sync' en el menú de aplicaciones de tu Linux,"
echo "anclarlo a tus favoritos, o iniciarlo directamente."
echo "Carpeta física local a configurar para sincronización: ~/KognitoSync (o la que tú elijas)"
echo "=================================================="
